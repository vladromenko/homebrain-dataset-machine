"""Start and stop only processes identified as belonging to this application."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
import psutil
from .config import load,ROOT


def start(name, args, config):
    runtime = Path(config["runtime"])
    pidfile = runtime/(name+".json")
    if identity(pidfile):
        return
    log = (runtime/(name+".log")).open("ab")
    proc = subprocess.Popen(args,cwd=ROOT,stdout=log,stderr=log,start_new_session=True,
                            env={**os.environ,"OMP_NUM_THREADS":"2","OPENBLAS_NUM_THREADS":"1"})
    pidfile.write_text(json.dumps({"pid":proc.pid,"created":psutil.Process(proc.pid).create_time(),"args":args}))


def identity(path):
    try:
        record = json.loads(path.read_text())
        process = psutil.Process(record["pid"])
        valid = abs(process.create_time()-record["created"])<.01 and process.status()!=psutil.STATUS_ZOMBIE
        return process if valid else None
    except (OSError,ValueError,psutil.Error):
        return None


def stop(config, name):
    path = Path(config["runtime"])/(name+".json")
    process = identity(path)
    if process:
        process.terminate()
        try:
            process.wait(timeout=8)
        except psutil.TimeoutExpired:
            print(f"{name} did not exit; left running rather than killing it")
            return
    path.unlink(missing_ok=True)


def model_args(config):
    work = Path(config["work"])
    build = "build" if config["gpu_layers"] else "build-cpu"
    binary = work/"vendor/llama.cpp"/build/"bin/llama-server"
    args = [str(binary),"-m",str(work/"models"/config["model"]/"model.gguf"),
            "--host","127.0.0.1","--port",str(config["model_port"]),"-c",str(config["context"]),
            "-t",str(config["threads"]),"-ngl",str(config["gpu_layers"]),"-np","1","--jinja",
            "-b","64","-ub","64","--cache-ram","0","--repack" if config.get("model_repack",True) else "--no-repack","--load-mode",config.get("model_load_mode","none"),"--sleep-idle-seconds","30"]
    if config["model"] == "gemma":
        args += ["--mmproj",str(work/"models/gemma/mmproj.gguf"),"--no-mmproj-offload"]
    return args


def main():
    config = load()
    action = sys.argv[1] if len(sys.argv)>1 else "start"
    if action in ("stop","unload"):
        (Path(config["runtime"])/"model-disabled").touch()
        if action == "stop":
            stop(config,"web")
            stop(config,"perception")
        stop(config,"model")
    elif action == "status":
        for name in ("web","model"):
            print(name, "running" if identity(Path(config["runtime"])/(name+".json")) else "stopped")
    else:
        (Path(config["runtime"])/"model-disabled").unlink(missing_ok=True)
        args = model_args(config)
        if config.get("manage_models",True) and Path(args[0]).exists():
            start("model",["nice","-n","15"]+args,config)
        else:
            print("Model runtime is still building; grounded project tools are available.")
        start("web",[str(ROOT/".venv/bin/python"),"-m","uvicorn","homebrain.app:app",
                     "--host","127.0.0.1","--port",str(config["port"]),"--no-access-log"],config)
        print(f'Homebrain AI: http://localhost:{config["port"]} (private SSH forwarding supported)')


if __name__ == "__main__":
    main()
