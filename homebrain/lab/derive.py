"""Derived local RRD view; native MCAP remains the source of truth."""
import hashlib
import json
import sys
from pathlib import Path
import rerun as rr


def derive(source, destination):
    rr.init('homebrain-native-observation-replay', spawn=False)
    rr.save(str(destination))
    digest = hashlib.file_digest(source.open('rb'), 'sha256').hexdigest()
    rr.log('provenance', rr.TextDocument(json.dumps({'source_sha256': digest, 'source_format': 'native MCAP',
        'view_format': 'derived RRD', 'training_eligible': False, 'world_transform': 'native frames only; no invented calibration'})), static=True)
    rr.log_file_from_path(str(source))
    rr.get_global_data_recording().flush(timeout_sec=60)
    rr.disconnect()
    return {'source_sha256': digest, 'derived_bytes': destination.stat().st_size}


if __name__ == '__main__':
    result = derive(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(result))
