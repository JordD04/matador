# coding: utf-8
""" This module contains functionality to update
and overwrite database entries with specific tasks,
e.g. symmetry and substructure analysis.
"""

from __future__ import print_function
# matador modules
from .utils.print_utils import print_notify, print_warning, print_failure
# external library
import pymongo as pm
# standard library
from sys import exit
from traceback import print_exc


class Refiner:
    """ Refiner implements methods to alter certain parts of the
    database in place, either in overwrite, set or compare/display mode.
    Current modifiables are space groups, substructures, atomic ratios,
    the set of elements, tags and DOIs.
    """

    def __init__(self, cursor, collection=None, task=None, mode='display', **kwargs):
        """ Parses args and initiates modification. """
        possible_tasks = ['sym', 'spg',
                          'substruc', 'sub',
                          'elem_set',
                          'ratios',
                          'tag',
                          'doi']
        possible_modes = ['display', 'overwrite', 'set']
        if mode not in possible_modes:
            print('Mode not understood, defaulting to "display".')
            mode = 'display'
        if collection is None and mode in ['overwrite', 'set']:
            exit('Impossible to overwite or set without db collection, exiting...')
        if task is None:
            exit('No specified task, exiting...')
        elif task not in possible_tasks:
            exit('Did not understand task, please choose one of ' + ', '.join(possible_tasks))
        if task == 'tag' and mode == 'set':
            print_notify('Task \'tags\' and mode \'set\' will not alter the database, ' +
                         'please use mode \'overwrite\'.')
            exit()

        self.cursor = cursor
        self.diff_cursor = []
        self.collection = collection
        self.mode = mode
        self.changed_count = 0
        self.failed_count = 0
        self.args = kwargs

        if task == 'spg' or task == 'sym':
            if kwargs.get('symprec'):
                self.symmetry(symprec=kwargs.get('symprec'))
            else:
                self.symmetry()
            self.field = 'space_group'
        elif task == 'substruc' or task == 'sub':
            self.substruc()
            self.field = 'substruc'
        elif task == 'ratios':
            self.ratios()
            self.field = 'ratios'
        elif task == 'elem_set':
            self.elem_set()
            self.field = 'elems'
        elif task == 'tag':
            self.field = 'tags'
            self.tag = self.args.get('new_tag')
            print(self.tag)
            if self.tag is None:
                print_warning('No new tag defined, nothing will be done.')
            else:
                self.add_tag()
        elif task == 'doi':
            self.field = 'doi'
            self.doi = self.args.get('new_doi')
            if self.doi is None:
                print_warning('No new DOI defined, nothing will be done.')
            else:
                self.add_doi()
        try:
            self.cursor.close()
        except Exception as oops:
            if self.args.get('debug'):
                print(repr(oops))
            pass
        try:
            print(self.changed_count, '/', len(self.cursor), 'to be changed.')
            print(self.failed_count, '/', len(self.cursor), 'failed.')
        except:
            print(self.changed_count, '/', self.cursor.count(), 'to be changed.')
            print(self.failed_count, '/', self.cursor.count(), 'failed.')

        if self.mode in ['set', 'overwrite'] and self.changed_count > 0:
            self.update_docs()

    def update_docs(self):
        """ Updates documents in database with correct priority. """
        requests = []
        # if in "set" mode, do not overwrite, just apply
        if self.mode == 'set':
            for ind, doc in enumerate(self.diff_cursor):
                requests.append(pm.UpdateOne({'_id': doc['_id'], self.field: {'$exists': False}}, {'$set': {self.field: doc[self.field]}}))
        # else if in overwrite mode, overwrite previous field
        elif self.mode == 'overwrite':
            for ind, doc in enumerate(self.diff_cursor):
                requests.append(pm.UpdateOne({'_id': doc['_id']}, {'$set': {self.field: doc[self.field]}}))
        if self.args.get('debug'):
            for request in requests:
                print(request)

        result = self.collection.bulk_write(requests)
        print_notify(str(result.modified_count) + ' docs modified.')

    def substruc(self):
        """ Compute substructure with Can's Voronoi code. """
        from voronoi_interface import get_voronoi_substructure
        print('Performing substructure analysis...')
        for ind, doc in enumerate(self.cursor):
            try:
                self.changed_count += 1
                doc['substruc'] = get_voronoi_substructure(doc)
                self.diff_cursor.append(doc)
            except:
                self.failed_count += 1
                if self.args.get('debug'):
                    print_exc()
                    print_failure('Failed for' + ' '.join(doc['text_id']))
                pass
        if self.mode == 'display':
            for doc in self.diff_cursor:
                print(doc['substruc'])

    def symmetry(self, symprec=1e-3):
        """ Compute space group with spglib. """
        from .utils.cell_utils import doc2spg
        import spglib as spg
        print('Refining symmetries...')
        if self.mode == 'display':
            print_warning('{}'.format('At symprec: ' + str(symprec)))
            print_warning("{:^36}{:^16}{:^16}".format('text_id', 'new sg', 'old sg'))
        for ind, doc in enumerate(self.cursor):
            try:
                spg_cell = doc2spg(doc)
                sg = spg.get_spacegroup(spg_cell, symprec=symprec).split(' ')[0]
                if sg != doc['space_group']:
                    self.changed_count += 1
                    self.diff_cursor.append(doc)
                    if self.mode == 'display':
                        print_notify("{:^36}{:^16}{:^16}".format(doc['text_id'][0]+' '+doc['text_id'][1], sg, doc['space_group']))
                    doc['space_group'] = sg
                else:
                    if self.mode == 'display':
                        print("{:^36}{:^16}{:^16}".format(doc['text_id'][0]+' '+doc['text_id'][1], sg, doc['space_group']))
            except:
                self.failed_count += 1
                if self.args.get('debug'):
                    print_exc()
                    print_failure('Failed for' + ' '.join(doc['text_id']))
                pass

    def ratios(self):
        """ Precompute stoichiometric ratios for use in
        non-binary voltage curves and hulls.

        Adds 'ratios' field to the docs, containing, e.g.

        Li2AsP:
        {
            LiAs: 2.0, AsLi: 0.5, PAs: 1.0,
            AsP: 1.0, LiP: 2.0, PLi: 0.5
        }
        """
        for ind, doc in enumerate(self.cursor):
            try:
                ratio_dict = dict()
                for i, elem_i in enumerate(doc['stoichiometry']):
                    for j, elem_j in enumerate(doc['stoichiometry']):
                        if elem_j != elem_i:
                            ratio_dict[doc['stoichiometry'][i][0]+doc['stoichiometry'][j][0]] = round(float(doc['stoichiometry'][i][1]) / doc['stoichiometry'][j][1], 3)
                if self.args.get('debug'):
                    print(ratio_dict)
                doc['ratios'] = ratio_dict
                self.diff_cursor.append(doc)
                self.changed_count += 1
            except:
                self.failed_count += 1
                pass

    def elem_set(self):
        """ Imbue documents with the set of elements,
        i.e. set(doc['atom_types']), for quicker look-up.
        """
        for ind, doc in enumerate(self.cursor):
            try:
                doc['elems'] = list(set(doc['atom_types']))
                self.diff_cursor.append(doc)
                self.changed_count += 1
            except Exception as oops:
                if self.args.get('debug'):
                    print(repr(oops))
                self.failed_count += 1
                pass

    def add_tag(self):
        """ Add a tag to each document. """
        for ind, doc in enumerate(self.cursor):
            try:
                if 'tags' in doc:
                    if doc['tags'] is None:
                        doc['tags'] = list()
                    else:
                        doc['tags'] = list(doc['tags'])
                    doc['tags'].append(self.tag)
                else:
                    doc['tags'] = [self.tag]
                self.diff_cursor.append(doc)
                self.changed_count += 1
            except Exception as error:
                print(repr(error))
                self.failed_count += 1
                pass

    def add_doi(self):
        """ Add a doi to each document. """
        if self.doi.count('/') != 1:
            print_warning('Malformed DOI... please use xxxxx/xxxxx format.')
            exit()
        for ind, doc in enumerate(self.cursor):
            try:
                if 'doi' in doc:
                    raise Exception('DOI already exists in doc, will skip for now...')
                else:
                    doc['doi'] = [self.doi]
                self.diff_cursor.append(doc)
                self.changed_count += 1
            except Exception as error:
                print(repr(error))
                self.failed_count += 1
                pass