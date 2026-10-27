"""Actual local research inference on generated pixels, no dataset/download/training."""
import io
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from clinical_skin_classifier import classify_clinical_skin_photo
from lesion_classifier import classify_dermoscopic_lesion
from nail_classifier import classify_nail_photo

if __name__=='__main__':
    image=Image.new('RGB',(384,384))
    image.putdata([((x*3+y)%200+20,(x+y*2)%180+30,(x*2+y*3)%160+40) for y in range(384) for x in range(384)])
    buffer=io.BytesIO();image.save(buffer,format='PNG')
    result=[]
    for name,function in [('ordinary_skin',classify_clinical_skin_photo),('dermoscopy',classify_dermoscopic_lesion),('nails',classify_nail_photo)]:
        started=time.perf_counter()
        try:
            response=function(buffer.getvalue())
            passed=bool(response.get('available') and response.get('top_predictions'))
            result.append(dict(adapter=name,actual_inference=passed,rankings=len(response.get('top_predictions',[])),seconds=round(time.perf_counter()-started,3)))
        except Exception:
            result.append(dict(adapter=name,actual_inference=False,reason='Local adapter smoke failed; inspect versions/checksums without logging inputs.'))
    print(json.dumps(dict(synthetic_pixels_only=True,clinical_validation=False,results=result),indent=2))
    raise SystemExit(0 if all(r['actual_inference'] for r in result) else 1)
