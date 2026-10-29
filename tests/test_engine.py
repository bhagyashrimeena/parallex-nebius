import io
import pytest
from PIL import Image
from app.engine import (
    InspectionError, load_and_normalize, parse_json_response, verify_findings, inspect_quality,
)

def test_unsupported_image_rejected():
    with pytest.raises(InspectionError):
        load_and_normalize(b'not a photo')

def test_quality_flags_dark():
    image=Image.new('RGB',(200,200),(4,4,4))
    result=inspect_quality(image,image.size)
    assert any('Underexposed' in x for x in result['flags'])
    assert 'Low resolution' in ' '.join(result['flags'])

def test_normalizes_exif_safe_and_resizes():
    image=Image.new('RGB',(2000,1000),(60,90,100))
    b=io.BytesIO();image.save(b,format='JPEG')
    converted,quality=load_and_normalize(b.getvalue())
    with Image.open(io.BytesIO(converted)) as normalized:
        assert max(normalized.size)==1600
    assert quality['width']==2000

def test_json_accepts_fences():
    assert parse_json_response('```json\n{"a":1}\n```')['a']==1

def test_invalid_json_rejected():
    with pytest.raises(InspectionError):parse_json_response('not json')

def test_evidence_gate_rejects_fabricated_refs():
    result=verify_findings({'summary':'ok','findings':[
        {'title':'Real','observation':'Visible line','evidence_ids':['P-01'],'priority':'high'},
        {'title':'Invented','observation':'Visible crack','evidence_ids':['P-99'],'priority':'high'},
        {'title':'No evidence','observation':'Maybe','evidence_ids':[]},
    ]},{'P-01'})
    assert len(result['findings'])==1
    assert result['findings'][0]['id']=='F-01'
    assert result['rejected_claims']==2
    assert 'excluded' in ' '.join(result['uncertainties'])

def test_unsupported_priority_is_unknown():
    result=verify_findings({'findings':[{'title':'X','observation':'Y','priority':'critical','evidence_ids':['P-01']}]},{'P-01'})
    assert result['findings'][0]['priority']=='unknown'
