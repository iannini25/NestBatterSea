"""PUT local files to Higgsfield presigned upload URLs. usage: python put.py jobs.json
jobs.json: {"local/path": ["upload_url", "content/type"], ...} (paths relative to _work)"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
jobs = json.load(open(sys.argv[1]))
for path, (url, ctype) in jobs.items():
    full = os.path.join(HERE, path)
    r = subprocess.run(['curl', '-s', '-o', os.devnull, '-w', '%{http_code}', '-X', 'PUT', '-H', 'Content-Type: ' + ctype,
                        '-H', 'If-None-Match: *', '--data-binary', '@' + full, url], capture_output=True, text=True)
    print(path, r.stdout, r.stderr[:200])
