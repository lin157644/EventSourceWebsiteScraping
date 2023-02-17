# EventGO

## Environment
- docker `ubuntu:20.04 `
  - package install
    - tmux
    - python
    - google-chrome-stable
    - ...
- port 8000 for FastAPI service
- recommend using docker data volume or `-v` tag


## Requirement
```
python 3.8.10
pip install -r requirement.txt
```

## Usage
- [.env](https://docs.google.com/document/d/12gDx4VBdtArxcNcmvhNdf_QNKW-m2wIqBf_mmytvUT4/edit?usp=share_link) file
  - place under project root directory `./EventGO/.env`
### In Docker (bash)
```
bash setup.sh
```

### Outside Docker (system)
```
# Event Source URLs Extaction & Automatic Pagination Recognition
docker exec -i EventGo bash -c "bash /root/EventGo/setup.sh"
# Event Post Checker
docker exec -i EventGo bash -c "bash /root/EventGo/post_checker.sh"
```
