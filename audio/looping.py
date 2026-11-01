"""Crossfade repeated score audio instead of clicking at a hard concatenation."""
import numpy as np

def loop_music(samples, frames, sample_rate, crossfade_seconds=2.):
    samples=np.asarray(samples)
    if samples.ndim==1:samples=samples[:,None]
    if not len(samples):raise ValueError('Music track is empty')
    if frames<=len(samples):return samples[:frames].copy()
    overlap=min(max(1,int(crossfade_seconds*sample_rate)),max(1,len(samples)//4))
    step=max(1,len(samples)-overlap)
    out=np.zeros((frames,samples.shape[1]),dtype=np.float64)
    for start in range(0,frames,step):
        length=min(len(samples),frames-start)
        weights=np.ones(length)
        if start:
            count=min(overlap,length)
            weights[:count]=np.sin(np.linspace(0,np.pi/2,count))**2
        if start+len(samples)<frames:
            count=min(overlap,length)
            weights[-count:]=np.cos(np.linspace(0,np.pi/2,count))**2
        out[start:start+length]+=samples[:length]*weights[:,None]
    return out
