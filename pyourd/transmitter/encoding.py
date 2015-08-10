from datetime import datetime
import traceback

import strict_rfc3339

from ..models import (
    Record,
    RecordID,
    RelationalAccessControlEntry,
    DirectAccessControlEntry,
    Asset,
    Reference,
)


def _serialize_exc(e):
    return {
        'name': str(e),
        'desc': traceback.format_exc(),
    }


def deserialize_record(obj):
    return _RecordDecoder().decode(obj)


def serialize_record(record):
    return _RecordEncoder().encode(record)


class _RecordDecoder:
    def decode(self, d):
        id = self.decode_id(d['_id'])
        del d['_id']

        owner_id = d['_ownerID']
        del d['_ownerID']

        acl = self.decode_acl(d['_access'])
        del d['_access']

        data_dict = {k: v for k, v in d.items() if not k.startswith('_')}

        data = self.decode_dict(data_dict)

        return Record(id=id, owner_id=owner_id, acl=acl, **data)

    def decode_id(self, s):
        ss = s.split('/')
        return RecordID(ss[0], ss[1])

    def decode_acl(self, l):
        if l is None:
            return None
        if not isinstance(l, list):
            raise TypeError('expect ACL to be a list')

        return [self.decode_ace(d) for d in l]

    def decode_ace(self, d):
        level = d['level']
        relation = d['relation']
        if relation == '$direct':
            return DirectAccessControlEntry(d['user_id'], level)
        else:
            return RelationalAccessControlEntry(relation, level)

    def decode_dict(self, d):
        return {k: self.decode_value(v) for k, v in d.items()}

    def decode_list(self, l):
        return [self.decode_value(v) for v in l]

    def decode_value(self, v):
        if isinstance(v, dict):
            type_ = v.get('$type')
            if type_ == 'date':
                return self.decode_date(v)
            elif type_ == 'asset':
                return self.decode_asset(v)
            elif type_ == 'ref':
                return self.decode_ref(v)
            else:
                return self.decode_dict(v)
        elif isinstance(v, list):
            return self.decode_list(v)
        else:
            return v

    def decode_date(self, d):
        ts = strict_rfc3339.rfc3339_to_timestamp(d['$date'])
        return datetime.utcfromtimestamp(ts)

    def decode_asset(self, d):
        return Asset(d['$name'])

    def decode_ref(self, d):
        return Reference(self.decode_id(d['$id']))


class _RecordEncoder:
    def encode(self, record):
        d = self.encode_dict(record.data)
        d['_id'] = self.encode_id(record.id)
        d['_ownerID'] = record.owner_id
        d['_access'] = self.encode_acl(record.acl)
        return d

    def encode_id(self, id):
        return '%s/%s' % (id.type, id.key)

    def encode_acl(self, acl):
        if acl is None:
            return None

        return [self.encode_ace(e) for e in acl]

    def encode_ace(self, ace):
        if isinstance(ace, RelationalAccessControlEntry):
            return {
                'level': ace.level,
                'relation': ace.relation,
            }
        elif isinstance(ace, DirectAccessControlEntry):
            return {
                'level': ace.level,
                'relation': '$direct',
                'user_id': ace.user_id,
            }
        else:
            raise ValueError('Unknown type of ACE = %s', type(ace))

    def encode_dict(self, d):
        return {k: self.encode_value(v) for k, v in d.items()}

    def encode_list(self, l):
        return [self.encode_value(v) for v in l]

    def encode_value(self, v):
        if isinstance(v, dict):
            return self.encode_dict(v)
        elif isinstance(v, list):
            return self.encode_list(v)
        elif isinstance(v, datetime):
            return self.encode_datetime(v)
        elif isinstance(v, Asset):
            return self.encode_asset(v)
        elif isinstance(v, Reference):
            return self.encode_ref(v)
        else:
            return v

    def encode_datetime(self, dt):
        ts = dt.timestamp()
        return {
            '$type': 'date',
            '$date': strict_rfc3339.timestamp_to_rfc3339_utcoffset(ts)
        }

    def encode_asset(self, asset):
        return {
            '$type': 'asset',
            '$name': asset.name,
        }

    def encode_ref(self, ref):
        return {
            '$type': 'ref',
            '$id': self.encode_id(ref.recordID),
        }