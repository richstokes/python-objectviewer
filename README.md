Debugging tool thats lets you easily inspect/visualize objects and variables in your running python code as a tree view.  

It uses the Debug Adapter Protocol (DAP) to retrieve the objects in your running python program. It then displays them in a web app.  

Every time you refresh the page, it briefly pauses your running code and displays a snapshot of its current state.  



#### Screenshot
![Screenshot](screenshot.png)


## Setup
On the project you wish to debug, install [debugpy](https://github.com/microsoft/debugpy):  
`pipenv install debugpy`



### Start debugpy server
From the project you with to debug:
```
pipenv run python -m debugpy --listen localhost:5678 your-script.py
```

### Run python-objectviewer
In another terminal, clone this repo and run:
`HD_PORT=9000 pipenv run python pov.py`

Then open your browser at [http://localhost:9000](http://localhost:9000)