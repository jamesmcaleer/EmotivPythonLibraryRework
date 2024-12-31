This repository features a rework of the [Emotiv Python](https://github.com/Emotiv/cortex-example/tree/master/python) library, specifically the [cortex.py](https://github.com/Emotiv/cortex-example/blob/master/python/cortex.py) file.

# Reason for rework
When I learned about the [Cortex API](https://emotiv.gitbook.io/cortex-api/overview-of-api-flow), I wanted to use the functions to build a GUI that lets users see the process of Authentication, connect to specific Headsets, choose/create a Subject, choose/create a Record, and more.

To do this, I thought to go to the [Github](https://github.com/Emotiv/cortex-example/tree/master/python) and use the [cortex.py](https://github.com/Emotiv/cortex-example/blob/master/python/cortex.py) library to call the API functions. I found that this file has too much control over the _flow_ of the application and limits what the developer can do.

For example, once the WebSocket is opened and the event _open_ is recieved, _on_open()_ calls a method _do_prepare_steps()_ which triggers a series of authentication, headset connection, and even starts a session.

Coming from the perspective of a developer, I wanted to have control over these steps. Maybe I want to choose a Subject before I create a session. Maybe I want a button that allows the user to select which headset to connect to.

To have this control, I realized I would have to rework cortex.py to fit my needs as a developer. 

# Demo

Using the new Cortex library to call the Cortex API and receieve the response can be done in four lines:
```
from cortex import Cortex # import Cortex library

cortex = Cortex(client_id, client_secret) # instantiate Cortex object - also opens WebSocket connection

result = cortex.await_response( api_call=self.cortex.get_user_login )
# make a request to the API with ^ 'await_response'

cortex.close() # closes the WebSocket connection
```

# Key Changes

## WebSocket Response Handling
**emit** result instead of **handle** result (and so on for error, warning, stream_data)

The 'handle' methods would be called when the WebSocket sends back a response. And depending on the API call, a different thing would happen.
ex: 
```
def handle_result(self, recv_dic):
  req_id = recv_dic['id']
  result_dic = recv_dic['result']
  if req_id == HAS_ACCESS_RIGHT_ID:
    access_granted = result_dic['accessGranted']
    if access_granted == True:
        # authorize
        self.authorize()
    else:
        # request access
        self.request_access()
```
This controls the flow of the program too much and does not give developers the chance to display UI or anything else in between these API calls.
My solution is replacing _handle_result()_ with _emit_result()_:
```
def emit_result(self, res_dic):
    # lets just get the result and emit it

    req_id = res_dic['id']
    result_dic = res_dic['result']

    self.emit(REQUEST_TO_EMIT[req_id], result_dic)
```
which takes the response of the WebSocket and emits it through an event.

Depending on the 'request_id', a different event is emitted, and there is an event for each API call/response.

## Use of bind() in the Cortex class
_bind()_ is what allows us to trigger a function call when an event is received.

In examples from the Emotiv repository, such as [record.py](https://github.com/Emotiv/cortex-example/blob/master/python/record.py), there would be a seperate class to serve as an example of how to use the Cortex library to call and handle API calls.
```
class Record():
    def __init__(self, app_client_id, app_client_secret, **kwargs):
        self.c = Cortex(app_client_id, app_client_secret, debug_mode=True, **kwargs)
        self.c.bind(create_session_done=self.on_create_session_done)
        self.c.bind(create_record_done=self.on_create_record_done)
```
And inside _these_ example classes would be the binding of API events to functions like _on_create_record_done()_ that do a certain action when the response from 'createRecord' is sent from the API.

The problem I saw in this approach is that the developer needs an _on_BLANK_done()_ method for every API event they use. It would be much easier if the developer could call the API, and have the response returned back in a single line.

That is why I created the bindings _inside_ the Cortex class, so that Cortex can listen for when these events are complete and send back to the developer the intended response.

```
class Cortex(Dispatcher):
  def __init__(self, ...):
    ...
    self.api_events = ['inform_error', 'get_cortex_info_done', 'get_user_login_done', ...]
    ...

    self.current_result = None
    self.response_event = threading.Event()
    
    for event in self.api_events:
        self.bind(**{event: self.on_request_done})
```

And then when the result of the API call is emitted, this method runs:
```
def on_request_done(self, result_dic):
  self.current_result = result_dic
  self.response_event.set()  # Signal that the response is ready
```

Lastly we have the method that the developer will be calling, so that they can easily call an API, and receieve the response:
```
def await_response(self, api_call, **kwargs):
        self.response_event.clear()  # Reset the event
        api_call(**kwargs)  # Call the provided API function
        self.response_event.wait()  # Wait for the corresponding event
        result_dic = self.current_result

        expected_event = api_call.__name__ + '_done'
        return result_dic
```

This works for **all** of the API functions listed in the Cortex API documentation.

I also created similar **warning** and **error** _emitters_ so that the developer has access to those values as well

## Support for all Cortex API functions

Another problem I noticed is that the functions in [cortex.py[(https://github.com/Emotiv/cortex-example/blob/master/python/cortex.py) don't take in all of the parameters that the API call requires.

This is because Cortex would store things such as the _token_ and _headset_id_ within the Cortex object, and automatically use that value for the API call.
```
def get_current_profile(self):
    print('get current profile:')
    get_profile_json = {
        "jsonrpc": "2.0",
        "method": "getCurrentProfile",
        "params": {
          "cortexToken": self.auth,
          "headset": self.headset_id,
        },
        "id": GET_CURRENT_PROFILE_ID
    }
    self.ws.send(json.dumps(get_profile_json))
```

I wanted these functions to match the documentation as close as possible, and also have the _developer_ manage variables such as the _token_, not Cortex.
```
def get_current_profile(self, cortex_token, headset_id):
    print('get current profile:')
    request = {
        "jsonrpc": "2.0",
        "method": "getCurrentProfile",
        "id": GET_CURRENT_PROFILE,
        "params": {
            "cortexToken": cortex_token,
            "headset": headset_id
        }
    }
    self.ws.send(json.dumps(request))
```
That is why **all** API functions require the parameters indicated in the Cortex API documentation.

Also, the previous cortex.py did not have support for some API calls, for example those relating the Subjects. So I added those in as well.

## Conclusion

While this does not cover _every_ change I made to the library, it covers the fundamental changes I made to make Cortex more accessible to developers.

I am thankful for the team at Emotiv for creating all of these tools as well as giving me the opportunity to learn more about how APIs and event-driven architecture work.

I hope that developers can find this rework useful for developing third-party Python applications with Emotiv EEG Headsets.





