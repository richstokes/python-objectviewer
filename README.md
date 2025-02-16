Debugging tool thats lets you easily inspect/visualize objects and variables in your running python code in real time.



## Setup
On the project you wish to debug, install `debugpy`:
`pipenv install debugpy`



## Start debugpy server
From the project you with to debug:
```
pipenv run python -m debugpy --listen localhost:5678 your-script.py
```


```
pipenv run python -m debugpy --listen localhost:5678 hdgol.py
```


## Run python-objectviewer
Clone this repo and run:
`HD_PORT=9000 pipenv run python pov.py`

Then open your browser at [http://localhost:9000](http://localhost:9000)