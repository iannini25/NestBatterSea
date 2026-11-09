# PUT each local file to its presigned Higgsfield URL (list of [file, url] in a JSON file).
import json, subprocess, sys
pairs = json.load(open(sys.argv[1]))
for f, url in pairs:
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '-X', 'PUT',
                        '-H', 'Content-Type: image/jpeg', '-H', 'If-None-Match: *',
                        '--data-binary', '@' + f, url], capture_output=True, text=True)
    print(r.stdout, f)
