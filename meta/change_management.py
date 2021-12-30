import copy
from dataclasses import dataclass, field
from django.db.models import Model
from django.db.transaction import atomic
from typing import Dict, List, Type
from uuid import UUID
from vycinity.meta.registries import ChangeableObjectRegistry
from vycinity.models import change_models

@dataclass
class ChangedObjectCollection:
    '''
    A dataclass for listing available and deleted, changed objects inside a changeset.
    '''
    avail: dict[type[Model], list[UUID]] = field(default_factory=dict)
    deleted: dict[type[Model], list[UUID]] = field(default_factory=dict)

def apply_changeset(changeset: change_models.ChangeSet):
    '''
    Applies a changeset to the current database. The changeset is applied in an atomic section, so
    either the whole changeset will be applied or it wont.
    '''
    ordered_changes: List[change_models.Change] = []
    for change in changeset.changes.all():
        position = len(ordered_changes)
        for dependent_change in change.dependents.all():
            for index in range(position):
                if ordered_changes[index] == dependent_change:
                    position = index
                    break
        ordered_changes.insert(position, change)
    
    changeable_object_registry = ChangeableObjectRegistry.instance()
    with atomic():
        for change in ordered_changes:
            type_metadata = changeable_object_registry.get(change.entity)
            if not type_metadata:
                raise Exception('Unknown entity \'{}\''.format(change.entity))
            if change.pre is None and change.post is not None:
                serializer = type_metadata.serializer(data=change.post)
                if serializer.is_valid():
                    serializer.save(id=change.new_uuid)
                else:
                    raise Exception('Entity in Change %s is not more valid.' % change.id)
            elif change.pre is not None and change.post is None and 'id' in change.pre:
                for_deletion = type_metadata.model.objects.get(id=UUID(change.pre['id']))
                for_deletion.delete()
            elif change.pre is not None and change.post is not None and 'id' in change.pre:
                serializer_data = copy.deepcopy(change.post)
                serializer = type_metadata.serializer(type_metadata.model.objects.get(id=UUID(change.pre['id'])), data=serializer_data)
                if serializer.is_valid():
                    serializer.save()
                else:
                    raise Exception('Entity in Change {:s} is not more valid.'.format(change.id))
            else:
                raise Exception('Change {:s} is invalid.'.format(change.id))

def get_known_changed_ids(changeset: change_models.ChangeSet) -> ChangedObjectCollection:
    '''
    Get all changed object uuids.

    params:
        changeset: The changeset to check.

    returns: A dict with model type as key and a list of uuids as value.
    '''
    rtn = ChangedObjectCollection()
    changeable_object_registry = ChangeableObjectRegistry.instance()
    for change in changeset.changes.all():
        change: change_models.Change
        model_type = changeable_object_registry.get(change.entity)
        if change.pre is None and change.post is not None:
            if model_type not in rtn.avail:
                rtn.avail[model_type] = []
            rtn.avail[model_type].append(change.new_uuid)
        elif change.pre is not None and change.post is not None:
            if model_type not in rtn.avail:
                rtn.avail[model_type] = []
            rtn.avail[model_type].append(UUID(change.pre['id']))
        elif change.pre is not None and change.post is None:
            if model_type not in rtn.deleted:
                rtn.deleted[model_type] = []
            rtn.deleted[model_type].append(UUID(change.pre['id']))
    return rtn