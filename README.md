# DeepStream Inconsistent Object IDs

Reproducible code for DeepStream issue specified on [Nvidia Developer Forum](https://forums.developer.nvidia.com/t/inconsistent-object-ids-when-running-on-multi-source-pipeline/232681/20)

Tested with:
|           | **DS** | **6.0.1**          | **6.1.1**          | **6.2**            |
|-----------|--------|--------------------|--------------------|--------------------|
| **pyds**  |        |                    |                    |                    |
| **1.1.4** |        | :heavy_check_mark: | :heavy_check_mark: |                    |
| **1.1.5** |        |                    |                    |                    |
| **1.1.6** |        |                    |                    | :heavy_check_mark: |

## Start command

```bash
# Start the docker container & select the DS and pyds version
./run.sh

# Run the inference code
python3 main.py -n {number of sources} --video-path {path to input video} --pgie-config {path to pgie config} --tracker-config {path to tracker config}
```
