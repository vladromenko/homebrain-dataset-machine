"""A local native fence extends only from actual focused browser packets."""
import os
import time
import uuid
from pathlib import Path
from .handover import directory, atomic


class NativeLeases:
    def __init__(self):
        self.folder = directory().parent/'leases'
        self.folder.mkdir(mode=0o700, exist_ok=True)
        self.entries = {}
        self.dataset_operations = {}

    def issue(self, session, generation, dataset=None):
        operation = uuid.uuid4().hex
        record = {'contract_version':'homebrain.lab.v1', 'operation_id':operation,
            'session_id':session, 'dataset_id':dataset, 'expected_generation':generation,
            'expires':time.monotonic()+.7, 'revoked':False, 'state':'intent', 'application_pid':os.getpid(),
            'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
        self.entries[operation] = record
        if dataset:
            self.dataset_operations[dataset] = operation
        self.write(record)
        return operation

    def write(self, record):
        atomic(self.folder/('operation-'+record['operation_id']+'.json'), record)
        if record['dataset_id'] and self.dataset_operations.get(record['dataset_id']) == record['operation_id']:
            atomic(self.folder/('dataset-'+record['dataset_id']+'.json'), record)

    def heartbeat(self, session):
        for record in list(self.entries.values()):
            if record['session_id'] == session and not record['revoked'] and record['state'] != 'done':
                record['expires'] = time.monotonic()+.7
                self.write(record)

    def revoke(self, session):
        for record in list(self.entries.values()):
            if record['session_id'] == session:
                record['revoked'] = True
                self.write(record)

    def finalize(self, session):
        for record in list(self.entries.values()):
            if record['session_id'] == session:
                record['state'] = 'finalizing'
                self.write(record)

    def complete(self, session):
        for record in list(self.entries.values()):
            if record['session_id'] == session:
                record['state'] = 'done'
                self.write(record)
