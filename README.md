# DeepStream Inconsistent Object IDs
Reproducible code for DeepStream issue specified on [Nvidia Developer Forum](https://forums.developer.nvidia.com/t/inconsistent-object-ids-when-running-on-multi-source-pipeline/232681/20)

Tested with:

- DeepStream version: 6.1.1
- pyds version: 1.1.4

## Start command

```bash
python3 deepstream.py -n {number of sources} --video-path {path to input video} --pgie-config {path to pgie config} --tracker-config {path to tracker config}
```
