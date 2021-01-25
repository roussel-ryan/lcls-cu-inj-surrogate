import json
import numpy as np
import pandas as pd


def collect_data(n_gen = 40):
    base = f'v1_cnsga/gen_1.json'
    with open(base) as f:
        data = json.load(f)

    #iterdict(data)
    output_ = pd.DataFrame(data['outputs'])


    input_ = pd.DataFrame(data['variables'])
    
    for i in range(n_gen):
        fname = f'v1_cnsga/pop_{i}.json'

        try: 
            with open(fname) as f:
                data = json.load(f)

            output_ = pd.concat((output_, pd.DataFrame(data['outputs'])))
            input_ = pd.concat((input_, pd.DataFrame(data['variables'])))
            
        except FileNotFoundError:
            pass
        
    #print(input_)
    #print(output_)

    return input_, output_
    
def iterdict(d, pad = 0):
    for k, v in d.items():
        if isinstance(v,dict):
            print(''.join(pad*[' ']) + k)
            iterdict(v, pad + 4)
        else:
            print(''.join((pad + 4)*[' ']) + k)
        
