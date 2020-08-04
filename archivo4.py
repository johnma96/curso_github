import pandas as import pd
import numpy as np
import matplotlib.pyplot as plt

x = np.arange(0,1)
y = x**2

df = pd.DataFrame(dict('x':x, 'y':y))

plt.plot(df.x, df.y)
