"""One explicit readiness probe, no recurring monitor or account access."""
import argparse,json,urllib.error,urllib.request
from urllib.parse import urlsplit

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8000');args=parser.parse_args()
    url=urlsplit(args.url)
    if url.scheme not in {'http','https'} or not url.netloc or url.username or url.password:parser.exit(2,'Use an application origin without credentials.\n')
    try:
        with urllib.request.urlopen(args.url.rstrip('/')+'/api/readiness',timeout=10) as response:data=json.load(response)
        print(json.dumps({key:data.get(key) for key in ['status','database','consumer_enabled','consumer_schema_ready','model_inference_tested']}))
        raise SystemExit(0 if data.get('status')=='ready' else 1)
    except (urllib.error.URLError,ValueError):parser.exit(1,'Readiness failed; no private response body logged.\n')
