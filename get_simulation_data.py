import numpy as np
import pandas as pd


def get_sim_data():
    X_df = pd.read_pickle('frontend/X.p')
    Y_df = pd.read_pickle('frontend/Y.p')

    #fix indicies
    X_df.reset_index(inplace = True, drop = True)
    Y_df.reset_index(inplace = True, drop = True)
    
    X_df_trans = transform_sim_inputs(X_df)
    
    df = pd.concat((X_df,X_df_trans,Y_df), axis = 1)
    return df


def transform_sim_inputs(X_df):
    mapping = pd.read_csv('pv_mapping/cu_inj_impact.csv')
    mapping.index = mapping['impact_name']

    scaled_simulation_pvs_raw = {}

    #print(X_df.keys())

    #drop distgen pulse length col (no conversion available)
    X_df = X_df.drop(labels = 'distgen:t_dist:length:value',axis = 1)
        
    for col_name, col_values in X_df.items():
        scale = mapping.loc[col_name]['impact_factor']
        device_name = mapping.loc[col_name]['device_pv_name']
        
        if 'IRIS' in device_name:
            scaled_simulation_pvs_raw['IRIS:LR20:130:MOTR_ANGLE'] = convert_iris_diameter(np.asfarray(col_values))

        else:
            scaled_simulation_pvs_raw[device_name] = np.asfarray(col_values) / scale

    scaled_simulation_pvs = pd.DataFrame(scaled_simulation_pvs_raw)

    return scaled_simulation_pvs

            
def convert_iris_diameter(X):
    fit_data = np.loadtxt('pv_mapping/iris_diameter_mapping.md', skiprows = 4, max_rows = 10)

    #linear fit to data
    z = np.polyfit(*fit_data.T,1)
    p = np.poly1d(z)
    #plt.plot(*fit_data.T[::-1])

    return p(X) * 3.0

    

if __name__=='__main__':
    df = get_sim_data()
    print(df['SOLN:IN20:121:BDES'].describe())
