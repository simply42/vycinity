import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from django.db.models import Model
from django.db.transaction import atomic
from typing import Dict, List, Type
from uuid import UUID
from vycinity.meta.registries import ChangeableObjectRegistry
from vycinity.models import OWNED_OBJECT_STATE_DELETED, OWNED_OBJECT_STATE_LIVE, OWNED_OBJECT_STATE_OUTDATED, OWNED_OBJECT_STATE_PREPARED, change_models

@dataclass
class ChangedObjectCollection:
    '''
    A dataclass for listing available and deleted, changed objects inside a changeset.
    '''
    avail: dict[type[Model], list[UUID]] = field(default_factory=dict)
    deleted: dict[type[Model], list[UUID]] = field(default_factory=dict)

class ChangeConflictError(Exception):
    '''
    An error class describing a conflict while applying a changeset.
    '''
    def __init__(self, message):
        self.message = message

def apply_changeset(changeset: change_models.ChangeSet):
    '''
    Applies a changeset to the current database. The changeset is applied in an atomic section, so
    either the whole changeset will be applied or it wont.

    May raise a ChangeConflictError if any of the changes is not based on a live object.
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
        if changeset.applied is not None:
            raise ChangeConflictError('Changeset with UUID {} has been already applied.'.format(changeset.id))
        for change in ordered_changes:
            # TODO: Check references
            type_metadata = changeable_object_registry.get(change.entity)
            if not type_metadata:
                raise Exception('Unknown entity \'{}\''.format(change.entity))
            if change.action == change_models.ACTION_CREATED:
                if change.pre is not None:
                    raise Exception('Change {} has action "{}" and a pre set.'.format(change.id, change_models.ACTION_CREATED))
                object = change.post
                if not object.owned_by(changeset.owner):
                    raise ChangeConflictError('Object owner of {} is not accessible by user.'.format(object.uuid, reference.uuid))
                dependencies = change.post.get_dependent_owned_objects()
                for reference in object.get_related_owned_objects():
                    if not (reference.owned_by(changeset.owner) or reference.public == True):
                        raise ChangeConflictError('Reference of object {} to {} is not allowed.'.format(object.uuid, reference.uuid))
                    if reference.state != OWNED_OBJECT_STATE_LIVE and reference in dependencies:
                        raise ChangeConflictError('Object {} points to a non live object {}.'.format(object.uuid, reference.uuid))
                object.state = OWNED_OBJECT_STATE_LIVE
                object.save()
            elif change.action == change_models.ACTION_DELETED:
                if change.pre is None or change.post is None:
                    raise Exception('Change {} has action "{}", but pre or post not set.'.format(change.id, change_models.ACTION_DELETED))
                if change.pre.state != OWNED_OBJECT_STATE_LIVE:
                    raise ChangeConflictError('{} with UUID {} has been changed before. This change bases on an older version.'.format(change.entity, change.pre.uuid))
                if not (change.post.owned_by(changeset.owner) and change.pre.owned_by(changeset.owner)):
                    raise ChangeConflictError('Object owner of {} is not accessible by user.'.format(object.uuid, reference.uuid))
                for reference in change.pre.get_related_owned_objects():
                    ref_dependencies = reference.get_dependent_owned_objects()
                    if change.pre in ref_dependencies and not reference.owned_by(changeset.owner) and reference.state == OWNED_OBJECT_STATE_LIVE:
                        raise ChangeConflictError('Object {} has a reference to object for deletion {}, but may not be modified to get unlinked.'.format(reference.uuid, change.pre.uuid))
                change.pre.state = OWNED_OBJECT_STATE_OUTDATED
                change.post.state = OWNED_OBJECT_STATE_DELETED
                change.pre.save()
                change.post.save()
            elif change.action == change_models.ACTION_MODIFIED:
                if change.pre is None or change.post is None:
                    raise Exception('Change {} has action "{}", but pre or post not set.'.format(change.id, change_models.ACTION_MODIFIED))
                if change.pre.state != OWNED_OBJECT_STATE_LIVE:
                    raise ChangeConflictError('{} with UUID {} has been changed before. This change bases on an older version.'.format(change.entity, change.pre.uuid))
                if change.post.state != OWNED_OBJECT_STATE_PREPARED:
                    raise ChangeConflictError('{} with UUID {} has been changed before. The new version is in invalid state.'.format(change.entity, change.post.uuid))
                if not (change.post.owned_by(changeset.owner) and change.pre.owned_by(changeset.owner)):
                    raise ChangeConflictError('Object owner of {} is not accessible by user.'.format(change.pre.uuid))
                dependencies = change.post.get_dependent_owned_objects()
                for reference in change.post.get_related_owned_objects():
                    if not (reference.owned_by(changeset.owner) or reference.public == True):
                        raise ChangeConflictError('Reference of object {} to {} is not allowed.'.format(change.post.uuid, reference.uuid))
                    if reference.state != OWNED_OBJECT_STATE_LIVE and reference in dependencies:
                        raise ChangeConflictError('Object {} points to a non live object {}.'.format(change.post.uuid, reference.uuid))
                change.pre.state = OWNED_OBJECT_STATE_OUTDATED
                change.post.state = OWNED_OBJECT_STATE_LIVE
                change.pre.save()
                change.post.save()
            else:
                raise Exception('Change {:s} is invalid.'.format(change.id))
        changeset.applied = datetime.now(timezone.utc)
        changeset.save()

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