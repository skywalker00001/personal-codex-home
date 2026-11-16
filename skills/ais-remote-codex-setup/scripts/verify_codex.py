#!/usr/bin/env python3
"""Verify real Codex authentication, configuration and enabled skills via app-server."""
import argparse
import json
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--require-skill',action='append',default=[])
    p.add_argument('--model-test',action='store_true')
    a=p.parse_args()
    cli=shutil.which('codex')
    if not cli:
        local=Path.home()/'.local/bin/codex'
        cli=str(local) if local.exists() else None
    if not cli:
        raise RuntimeError('codex is not installed or PATH is incomplete')
    print('CODEX_PATH',cli)
    subprocess.run([cli,'--version'],check=True)
    subprocess.run([cli,'login','status'],check=True)
    messages=queue.Queue()
    with tempfile.TemporaryFile() as err:
        proc=subprocess.Popen([cli,'app-server','--listen','stdio://'],stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1)
        def read():
            for line in proc.stdout:
                try:
                    messages.put(json.loads(line))
                except ValueError:
                    pass
        thread=threading.Thread(target=read,daemon=True)
        thread.start()
        def send(obj):
            proc.stdin.write(json.dumps(obj)+'\n');proc.stdin.flush()
        def result(msgid):
            end=time.monotonic()+45
            while time.monotonic()<end:
                try:
                    msg=messages.get(timeout=max(.1,end-time.monotonic()))
                except queue.Empty:
                    break
                if msg.get('id')==msgid:
                    if 'error' in msg:
                        raise RuntimeError('app-server rejected request; check current CLI protocol')
                    return msg['result']
            raise RuntimeError('app-server response timed out')
        try:
            send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'ais-setup-verifier','version':'1.0'},'capabilities':{'experimentalApi':True}}})
            result(1)
            send({'method':'initialized','params':{}})
            send({'id':2,'method':'skills/list','params':{'cwds':[str(Path.home())],'forceReload':True}})
            data=result(2)
            enabled=set()
            count=0
            for entry in data.get('data',[]):
                if entry.get('errors'):
                    raise RuntimeError('Codex reported skill loading errors')
                for skill in entry.get('skills',[]):
                    if skill.get('enabled'):
                        enabled.add(skill['name']);count+=1
            if not enabled:
                raise RuntimeError('No enabled skills returned; inspect protocol and discovery')
            absent=set(a.require_skill)-enabled
            print('ENABLED_SKILL_COUNT',count)
            for name in a.require_skill:
                print('REQUIRED_SKILL',name,'MISSING' if name in absent else 'OK')
            if absent:
                raise RuntimeError('Required skill missing/disabled')
            send({'id':3,'method':'config/read','params':{'includeLayers':False}})
            config=result(3).get('config',{})
            print('MODEL',config.get('model'),'REASONING',config.get('model_reasoning_effort'))
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill();proc.wait()
            thread.join(timeout=2)
    if a.model_test:
        r=subprocess.run([cli,'exec','--ephemeral','--sandbox','read-only','--skip-git-repo-check','--json',
                          '不要调用任何工具。仅回复 AIS_CODEX_MODEL_OK。'],capture_output=True,text=True,timeout=120,cwd=Path.home())
        messages=[]
        for line in r.stdout.splitlines():
            try:
                event=json.loads(line)
            except ValueError:continue
            if event.get('type')=='item.completed' and event.get('item',{}).get('type')=='agent_message':
                messages.append(event['item'].get('text',''))
        if r.returncode or not any('AIS_CODEX_MODEL_OK' in m for m in messages):
            raise RuntimeError('Live model test failed; inspect account/model availability')
        print('MODEL_CALL_OK')
    print('CODEX_RUNTIME_OK')


if __name__=='__main__':
    main()
