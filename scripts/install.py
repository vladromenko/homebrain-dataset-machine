"""Reproduce isolated local inference and assets without modifying the OS."""
import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda:source.read(4*1024**2),b""):
            result.update(block)
    return result.hexdigest()


def download_assets(work):
    rows = json.loads((ROOT/"assets.lock.json").read_text())
    for row in rows:
        destination = work/"models"/row["path"]
        destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists() or digest(destination)!=row["sha256"]:
            temporary = destination.with_suffix(destination.suffix+".part")
            urllib.request.urlretrieve(row["url"],temporary)
            if digest(temporary)!=row["sha256"]:
                raise ValueError("Asset checksum mismatch: "+row["path"])
            temporary.replace(destination)
        print("Verified",row["path"],flush=True)


def build(work):
    target = work/"vendor/llama.cpp"
    revision = json.loads((ROOT/"evaluation/environment.json").read_text())["llama_revision"]
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(["git","clone","--no-checkout","https://github.com/ggml-org/llama.cpp.git",str(target)],check=True)
        subprocess.run(["git","-C",str(target),"checkout",revision],check=True)
    actual = subprocess.check_output(["git","-C",str(target),"rev-parse","HEAD"],text=True).strip()
    if actual!=revision:
        raise ValueError("Existing runtime source revision differs; use a new private work directory")
    binary = target/"build-cpu/bin/llama-server"
    if not binary.exists():
        subprocess.run(["cmake","-S",str(target),"-B",str(target/"build-cpu"),"-DGGML_CUDA=OFF","-DLLAMA_BUILD_TESTS=OFF","-DLLAMA_BUILD_EXAMPLES=OFF","-DCMAKE_BUILD_TYPE=Release"],check=True)
        subprocess.run(["nice","-n","15","cmake","--build",str(target/"build-cpu"),"-j","2","--target","llama-server"],check=True)


def install_agents(work):
    target = work/'agent-runtime/opencode'
    target.mkdir(parents=True,exist_ok=True)
    for source,name in [('agent-runtime.package.json','package.json'),
                        ('agent-runtime.package-lock.json','package-lock.json')]:
        destination = target/name
        expected = json.loads((ROOT/source).read_text())
        if destination.exists() and json.loads(destination.read_text()) != expected:
            raise ValueError('Existing agent manifest differs; use a new private work directory')
        shutil.copyfile(ROOT/source,destination)
    if not (target/'node_modules/.bin/opencode').exists():
        subprocess.run(['npm','ci','--no-audit','--no-fund'],cwd=target,check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work",type=Path,required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True,exist_ok=True)
    config_path = ROOT/"config.local.json"
    config = json.loads((config_path if config_path.exists() else ROOT/"config.example.json").read_text())
    config["work"] = str(work)
    config_path.write_text(json.dumps(config,indent=2))
    download_assets(work)
    build(work)
    install_agents(work)
    print("Installation complete. Run ./homebrain.sh start")


if __name__=="__main__":
    main()
