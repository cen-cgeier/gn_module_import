from pathlib import Path
from copy import deepcopy

import pytest
from flask import testing, url_for
from werkzeug.datastructures import Headers
from werkzeug.exceptions import Unauthorized, Forbidden, BadRequest, Conflict, NotFound
from jsonschema import validate as validate_json
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from geonature.utils.env import db
from geonature.tests.utils import set_logged_user_cookie
from geonature.core.gn_permissions.tools import UserCruved
from geonature.core.gn_permissions.models import TActions, TFilters, CorRoleActionFilterModuleObject
from geonature.core.gn_commons.models import TModules
from geonature.core.gn_meta.models import TNomenclatures, TAcquisitionFramework, TDatasets

from pypnnomenclature.models import BibNomenclaturesTypes
from pypnusershub.db.models import User, Organisme, Application, Profils as Profil, UserApplicationRight

from gn_module_import.models import MappingTemplate, FieldMapping, ContentMapping, \
                                    BibThemes, BibFields, ImportUserError, ImportUserErrorType

from .jsonschema_definitions import jsonschema_definitions


tests_path = Path(__file__).parent



@pytest.fixture()
def mappings(users):
    mappings = {}
    fieldmapping_values = {
        field.name_field: field.name_field
        for field in BibFields.query.with_entities(BibFields.name_field)
    }
    contentmapping_values = {
        field.nomenclature_type.mnemonique: {
            nomenclature.cd_nomenclature: nomenclature.cd_nomenclature
            for nomenclature in field.nomenclature_type.nomenclatures
        }
        for field in (
                BibFields.query
                .filter(BibFields.nomenclature_type != None)
                .options(
                    joinedload(BibFields.nomenclature_type)
                        .joinedload(BibNomenclaturesTypes.nomenclatures),
                )
        )
    }
    with db.session.begin_nested():
        mappings['content_public'] = ContentMapping(label='Content Mapping', active=True, public=True, values=contentmapping_values)
        mappings['field_public'] = FieldMapping(label='Public Field Mapping', active=True, public=True, values=fieldmapping_values)
        mappings['field'] = FieldMapping(label='Private Field Mapping', active=True, public=False)
        mappings['field_public_disabled'] = FieldMapping(label='Disabled Public Field Mapping', active=False, public=True)
        mappings['self'] = FieldMapping(label='Self’s Mapping', active=True, public=False, owners=[users['self_user']])
        mappings['stranger'] = FieldMapping(label='Stranger’s Mapping', active=True, public=False, owners=[users['stranger_user']])
        mappings['associate'] = FieldMapping(label='Associate’s Mapping', active=True, public=False, owners=[users['associate_user']])
        db.session.add_all(mappings.values())
    return mappings


@pytest.mark.usefixtures("client_class", "temporary_transaction")
class TestMappings:
    def test_list_mappings(self, users, mappings):
        set_logged_user_cookie(self.client, users['noright_user'])

        r = self.client.get(url_for('import.list_mappings', mappingtype='field'))
        assert(r.status_code == Forbidden.code)

        set_logged_user_cookie(self.client, users['admin_user'])

        r = self.client.get(url_for('import.list_mappings', mappingtype='field'))
        assert(r.status_code == 200)
        validate_json(r.get_json(), {
            'definitions': jsonschema_definitions,
            'type': 'array',
            'items': { '$ref': '#/definitions/mapping' },
            'minItems': len(mappings),
        })


    def test_get_mapping(self, users, mappings):
        get_mapping = lambda mapping: self.client.get(url_for('import.get_mapping', mappingtype=mapping.type.lower(), id_mapping=mapping.id))

        assert get_mapping(mappings['field_public']).status_code == Unauthorized.code

        set_logged_user_cookie(self.client, users['noright_user'])

        assert get_mapping(mappings['field_public']).status_code == Forbidden.code

        set_logged_user_cookie(self.client, users['self_user'])

        r = self.client.get(url_for('import.get_mapping', mappingtype='unexisting', id_mapping=mappings['content_public'].id))
        assert r.status_code == NotFound.code

        r = self.client.get(url_for('import.get_mapping', mappingtype='field', id_mapping=mappings['content_public'].id))
        assert r.status_code == NotFound.code

        unexisting_id = db.session.query(func.max(MappingTemplate.id)).scalar() + 1
        r = self.client.get(url_for('import.get_mapping', mappingtype='field', id_mapping=unexisting_id))
        assert r.status_code == NotFound.code

        assert get_mapping(mappings['content_public']).status_code == 200
        assert get_mapping(mappings['field_public']).status_code == 200
        assert get_mapping(mappings['field']).status_code == Forbidden.code
        assert get_mapping(mappings['field_public_disabled']).status_code == Forbidden.code

        assert get_mapping(mappings['self']).status_code == 200
        assert get_mapping(mappings['associate']).status_code == Forbidden.code
        assert get_mapping(mappings['stranger']).status_code == Forbidden.code

        set_logged_user_cookie(self.client, users['user'])

        assert get_mapping(mappings['self']).status_code == 200
        assert get_mapping(mappings['associate']).status_code == 200
        assert get_mapping(mappings['stranger']).status_code == Forbidden.code

        set_logged_user_cookie(self.client, users['admin_user'])

        assert get_mapping(mappings['self']).status_code == 200
        assert get_mapping(mappings['associate']).status_code == 200
        assert get_mapping(mappings['stranger']).status_code == 200

        fm = get_mapping(mappings['field_public']).json
        FieldMapping.validate_values(fm['values'])
        cm = get_mapping(mappings['content_public']).json
        ContentMapping.validate_values(cm['values'])


    #def test_mappings_permissions(self, users, mappings):
    #    set_logged_user_cookie(self.client, users['self_user'])

    #    r = self.client.get(url_for('import.list_mappings', mappingtype='field'))
    #    assert(r.status_code == 200)
    #    mapping_ids = [ mapping['id_mapping'] for mapping in r.get_json() ]
    #    assert(mappings['content_public'].id_mapping not in mapping_ids)  # wrong mapping type
    #    assert(mappings['field_public'].id_mapping in mapping_ids)
    #    assert(self.client.get(url_for('import.get_mapping', id_mapping=mappings['field_public'].id_mapping)).status_code == 200)
    #    assert(mappings['field'].id_mapping not in mapping_ids)  # not public
    #    assert(self.client.get(url_for('import.get_mapping', id_mapping=mappings['field'].id_mapping)).status_code == Forbidden.code)
    #    assert(mappings['field_public_disabled'].id_mapping not in mapping_ids)  # not active
    #    assert(self.client.get(url_for('import.get_mapping', id_mapping=mappings['field_public_disabled'].id_mapping)).status_code == Forbidden.code)
    #    assert(mappings['self'].id_mapping in mapping_ids)  # not public but user is owner
    #    assert(self.client.get(url_for('import.get_mapping', id_mapping=mappings['self'].id_mapping)).status_code == 200)
    #    assert(mappings['stranger'].id_mapping not in mapping_ids)  # not public and owned by another user
    #    assert(self.client.get(url_for('import.get_mapping', id_mapping=mappings['stranger'].id_mapping)).status_code == Forbidden.code)
    #    assert(mappings['associate'].id_mapping not in mapping_ids)  # not public and owned by an user in the same organism whereas read scope is 1
    #    assert(self.client.get(url_for('import.get_mapping', id_mapping=mappings['associate'].id_mapping)).status_code == Forbidden.code)

    #    set_logged_user_cookie(self.client, users['user'])

    #    # refresh mapping list
    #    r = self.client.get(url_for('import.list_mappings', mappingtype='field'))
    #    mapping_ids = [ mapping['id_mapping'] for mapping in r.get_json() ]
    #    assert(mappings['stranger'].id_mapping not in mapping_ids)  # not public and owned by another user
    #    assert(self.client.get(url_for('import.get_mapping', id_mapping=mappings['stranger'].id_mapping)).status_code == Forbidden.code)
    #    assert(mappings['associate'].id_mapping in mapping_ids)  # not public but owned by an user in the same organism whereas read scope is 2
    #    assert(self.client.get(url_for('import.get_mapping', id_mapping=mappings['associate'].id_mapping)).status_code == 200)

    #    set_logged_user_cookie(self.client, users['admin_user'])

    #    # refresh mapping list
    #    r = self.client.get(url_for('import.list_mappings', mappingtype='field'))
    #    mapping_ids = [ mapping['id_mapping'] for mapping in r.get_json() ]
    #    assert(mappings['stranger'].id_mapping in mapping_ids)  # not public and owned by another user but we have scope = 3
    #    assert(self.client.get(url_for('import.get_mapping', id_mapping=mappings['stranger'].id_mapping)).status_code == 200)


    def test_add_field_mapping(self, users, mappings):
        fieldmapping = {
            "WKT": "geometrie",
            "cd_hab": "cdhab",
            "cd_nom": "cdnom",
        }
        url = url_for('import.add_mapping', mappingtype='field')

        assert self.client.post(url, data=fieldmapping).status_code == Unauthorized.code

        set_logged_user_cookie(self.client, users['user'])

        # label is missing
        assert self.client.post(url, data=fieldmapping).status_code == BadRequest.code

        # label already exist
        url = url_for('import.add_mapping', mappingtype='field', label=mappings['field'].label)
        assert self.client.post(url, data=fieldmapping).status_code == Conflict.code

        # label may be reused between field and content
        url = url_for('import.add_mapping', mappingtype='field', label=mappings['content_public'].label)

        r = self.client.post(url, data={"unexisting": "source column"})
        assert r.status_code == BadRequest.code

        r = self.client.post(url, data=fieldmapping)
        assert r.status_code == 200
        assert r.json['label'] == mappings['content_public'].label
        assert r.json['type'] == 'FIELD'
        assert r.json['values'] == fieldmapping
        mapping = MappingTemplate.query.get(r.json['id'])
        assert mapping.owners == [users['user']]


    def test_add_content_mapping(self, users, mappings):
        url = url_for('import.add_mapping', mappingtype='content', label='test content mapping')
        set_logged_user_cookie(self.client, users['user'])

        contentmapping = {
            'NAT_OBJ_GEO': {
                'ne sais pas': 'invalid',
            },
        }
        r = self.client.post(url, data=contentmapping)
        assert r.status_code == BadRequest.code

        contentmapping = {
            'NAT_OBJ_GEO': {
                'ne sais pas': 'NSP',
                'ne sais toujours pas': 'NSP',
            },
        }
        r = self.client.post(url, data=contentmapping)
        assert r.status_code == 200
        assert r.json['label'] == 'test content mapping'
        assert r.json['type'] == 'CONTENT'
        assert r.json['values'] == contentmapping
        mapping = MappingTemplate.query.get(r.json['id'])
        assert mapping.owners == [users['user']]


    def test_update_mapping_label(self, users, mappings):
        mapping = mappings["associate"]
        url = url_for('import.update_mapping', mappingtype=mapping.type.lower(), id_mapping=mapping.id)

        r = self.client.post(url_for('import.update_mapping', mappingtype=mapping.type.lower(), id_mapping=mapping.id))
        assert r.status_code == Unauthorized.code

        set_logged_user_cookie(self.client, users["self_user"])

        r = self.client.post(url_for('import.update_mapping', mappingtype=mapping.type.lower(), id_mapping=mapping.id))
        assert r.status_code == Forbidden.code

        set_logged_user_cookie(self.client, users["user"])

        r = self.client.post(url_for('import.update_mapping', mappingtype=mapping.type.lower(), id_mapping=mapping.id, label=mappings["field"].label))
        assert r.status_code == Conflict.code

        r = self.client.post(url_for('import.update_mapping', mappingtype="content", id_mapping=mapping.id, label="New mapping label"))
        assert r.status_code == NotFound.code

        r = self.client.post(url_for('import.update_mapping', mappingtype=mapping.type.lower(), id_mapping=mapping.id, label="New mapping label"))
        assert r.status_code == 200
        assert mappings["associate"].label == "New mapping label"


    def test_update_field_mapping_values(self, users, mappings):
        set_logged_user_cookie(self.client, users["admin_user"])

        fm = mappings["field_public"]
        fieldvalues2 = deepcopy(fm.values)
        fieldvalues2['WKT'] = 'WKT2'
        r = self.client.post(url_for('import.update_mapping', mappingtype=fm.type.lower(), id_mapping=fm.id), data=fieldvalues2)
        assert r.status_code == 200
        assert fm.values == fieldvalues2
        fieldvalues3 = deepcopy(fm.values)
        fieldvalues3['unexisting'] = 'unexisting'
        r = self.client.post(url_for('import.update_mapping', mappingtype=fm.type.lower(), id_mapping=fm.id), data=fieldvalues3)
        assert r.status_code == BadRequest.code
        assert fm.values == fieldvalues2

    def test_update_content_mapping_values(self, users, mappings):
        set_logged_user_cookie(self.client, users["admin_user"])
        cm = mappings["content_public"]
        contentvalues2 = deepcopy(cm.values)
        contentvalues2['NAT_OBJ_GEO']['ne sais pas'] = 'NSP'
        r = self.client.post(url_for('import.update_mapping', mappingtype=cm.type.lower(), id_mapping=cm.id), data=contentvalues2)
        assert r.status_code == 200
        assert cm.values == contentvalues2
        contentvalues3 = deepcopy(cm.values)
        contentvalues3['NAT_OBJ_GEO'] = 'invalid'
        r = self.client.post(url_for('import.update_mapping', mappingtype=cm.type.lower(), id_mapping=cm.id), data=contentvalues3)
        assert r.status_code == BadRequest.code
        assert cm.values == contentvalues2


    def test_delete_mapping(self, users, mappings):
        mapping = mappings['associate']
        r = self.client.delete(
            url_for('import.delete_mapping', mappingtype=mapping.type.lower(), id_mapping=mapping.id)
        )
        assert r.status_code == Unauthorized.code
        assert MappingTemplate.query.get(mapping.id) is not None

        set_logged_user_cookie(self.client, users["self_user"])
        r = self.client.delete(
            url_for('import.delete_mapping', mappingtype=mapping.type.lower(), id_mapping=mapping.id)
        )
        assert r.status_code == Forbidden.code
        assert MappingTemplate.query.get(mapping.id) is not None

        set_logged_user_cookie(self.client, users["user"])
        r = self.client.delete(
            url_for('import.delete_mapping', mappingtype='content', id_mapping=mapping.id)
        )
        assert r.status_code == NotFound.code
        assert MappingTemplate.query.get(mapping.id) is not None

        r = self.client.delete(
            url_for('import.delete_mapping', mappingtype=mapping.type.lower(), id_mapping=mapping.id)
        )
        assert r.status_code == 204
        assert MappingTemplate.query.get(mapping.id) is None


    def test_synthesis_fields(self, users):
        assert(self.client.get(url_for('import.get_synthesis_fields')).status_code == Unauthorized.code)
        set_logged_user_cookie(self.client, users["admin_user"])
        r = self.client.get(url_for('import.get_synthesis_fields'))
        assert(r.status_code == 200)
        data = r.get_json()
        themes_count = BibThemes.query.count()
        schema = {
            'definitions': jsonschema_definitions,
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'theme': { '$ref': '#/definitions/synthesis_theme' },
                    'fields': {
                        'type': 'array',
                        'items': { '$ref': '#/definitions/synthesis_field' },
                        'uniqueItems': True,
                        'minItems': 1,
                    }
                },
                'required': [
                    'theme',
                    'fields',
                ],
                'additionalProperties': False,
            },
            'minItems': themes_count,
            'maxItems': themes_count,
        }
        validate_json(data, schema)
