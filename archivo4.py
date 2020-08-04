import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

x = np.arange(0,1,100)
y = x**2

dictionary = {'x':x, 'y':y}

df = pd.DataFrame(dictionary)

print(df)
