import os
import time
import numpy as np
import pandas as pd
import pandas_bokeh
from datetime import datetime
from jinja2 import Template
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.io import output_file, output_notebook
from bokeh.plotting import figure, show
from bokeh.layouts import row, column, gridplot
from bokeh.models.widgets import Tabs, Panel
from bokeh.models import ColumnDataSource, HoverTool, Legend
SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
SUP = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")

output_notebook()

class Sensor:
    def __init__(self, name = None, database = 'Flux', days = 1,
    all_range = True, Temp_resolution = None,type_v = 'rawdata'):

        '''
        Input
        - name: String type. Name used to identify the sensor in the database.
                You can use any of the names within the list:

            [IRGASON_Candelaria, IRGASON_Federico_Carrasquilla, IRGASON_SENA,
            IRGASON_CASD_10M, IRGASON_ITM, IRGASON_Villa_Niza, IRGASON_CASD_20M,
            IRGASON_Jesus_Maria_Valle, IRGASON_Villa_Socorro,IRGASON_CASD_30M]

        - database: Search database. Default is Flux. It can be 'Flux' or 'Raw'.
            'Flux' coresponds to databases with procesing by software EasyFlux.
            'Raw' corresponds to data measured at 0.5s resolution
        - days: Int or list. Default is 1. Format to dates in list must be '%Y-%m-%d'.
                If is int, is obtained a DataFrame with data of actual day.
                If you enter a list with dates is obtained a DataFrame than start in
                the first day, and ends in the last day. If the list containd multiples
                dates is obtained a DataFrame wiht data in each date.
        - all_range: Default is True. If you just want the two dates, put in False
        - resolution: Temporary resolution of de data as int. Default is 0.05s
        - type_v: String with type of mesurements. It can be 'rawdata' or 'anomalies'.
                  Default is 'rawdata'. If you pass 'anomalies', it is calculated as

                                anomaly = value - average corresponding to 30min
        '''
        self.name = name
        self.path_data = '/var/data1/DatosTurbulencia/'+self.name
        self.days = days
        self.all_range = all_range
        self.resolution = Temp_resolution
        self.type_v = type_v
        self.database = database
        self.data = self.__database()
        print()

    def __database(self):

        #Select of database
        if self.database == 'Flux':
            dir_csv = self.path_data+'/Datos_Flux/'
        elif self.database == 'Raw':
            dir_csv = self.path_data+'/Datos_TS_DATA/'
        else:
            print(self.database)
            print('Ingrese una ruta apropiada ') #Agregar como una excepción

        files = os.listdir(dir_csv)

        if self.database == 'Raw':
            arc_csv = sorted([fn for fn in files if fn.startswith('Time_Series_2020') if fn.endswith('.csv')])
        elif self.database == 'Flux':
            arc_csv = sorted([fn for fn in files if fn.startswith('Flux_CSIFormat_2020') if fn.endswith('.csv')])

        #File selection

        #DataFrame from current day, X days back
        if isinstance(self.days, int):
            path_files = arc_csv[-self.days:]

        #DataFrame in specific period or in particular dates
        if isinstance(self.days,list):
            arc_csv = np.asarray(arc_csv)

            if len(self.days) == 2:  #If only two dates are supplied
                    self.start = self.days[0]
                    self.end = self.days[1]
                    order_dates, diff_dates = self.__verifyOrderDates(self.start, self.end)

                    if order_dates:
                        #Verifying that the date formats are correct
                        if self.database == 'Raw':
                            self.__a = ('Time_Series_'+self.start.date().strftime('%Y-%m-%d')+'.csv')
                            self.__b = ('Time_Series_'+self.end.date().strftime('%Y-%m-%d')+'.csv')
                        elif self.database == 'Flux':
                            self.__a = ('Flux_CSIFormat_'+self.start.date().strftime('%Y-%m-%d')+'.csv')
                            self.__b = ('Flux_CSIFormat_'+self.end.date().strftime('%Y-%m-%d')+'.csv')

                        #Select files to call
                        if self.__a and self.__b in arc_csv:
                            pos = np.where((arc_csv == self.__a) | (arc_csv == self.__b))[0]
                            if self.all_range: #All range between two dates
                                path_files = arc_csv[pos[0]:(pos[-1]+1)]
                            else: #Just the two dates
                                path_files= arc_csv[pos]
                        else:
                            print('El rango buscado no está disponible en la base de datos') #Agregar como excepcion

                    else:
                        print('El rango buscado no está disponible en la base de datos') #Agregar como excepcion


            elif len(self.days) != 2: #If multiple dates are supplied
                if self.database == 'Raw':
                    path_files = ['Time_Series_'+date+'.csv' for date in self.days if all('Time_Series_'+a+'.csv' in arc_csv for a in self.days)]
                elif self.database == 'Flux':
                    path_files = ['Flux_CSIFormat_'+date+'.csv' for date in self.days if all('Flux_CSIFormat_'+a+'.csv' in arc_csv for a in self.days)]

            else:
                print('El rango buscado no está disponible en la base de datos') #Agregar como excepcion
        self.__path_files = path_files
        print('Se cargarán las datos correspondientes a los archivos {} para la torre {}'.format(self.__path_files,
                                                                                             self.name))
        print()

        #Call data of interest
        data = self.__call_data(self.__path_files, dir_csv)

        #Change data resolution
        if self.resolution is not None:#Set up the temporary resolution of data
            data = self.__resolution(data)

        return data


    def __verifyOrderDates(self,start,end):

        self.start = datetime.strptime(start, '%Y-%m-%d')
        self.end = datetime.strptime(end, '%Y-%m-%d')
        order = self.end > self.start
        diff = self.end - self.start
        return (order, diff)

    def __resolution(self, df):

        df = (df.resample(self.resolution).mean())
        print('Cambio la resolución de los datos a '+self.resolution)
        return df

    def __call_data(self, path_files, dir_csv):

        rawdata = pd.DataFrame()
        anomalies = pd.DataFrame()
        for csv_ in sorted(path_files):
                day = int(csv_.split('-')[-1].split('.')[0])
                print('Leyendo el archivo {}'.format(csv_))
                try:

                    csv = pd.read_csv(dir_csv + csv_, sep = ',', header = [1], skiprows = [2, 3], na_values = 'NAN',
                                      skip_blank_lines = True, error_bad_lines = False,  warn_bad_lines = True,
                                      low_memory = False)

                    #Replace missing with nan
                    csv.replace(-99999., np.NaN, inplace = True)

                    #Organize and clean DataFrame
                    csv['TIMESTAMP'] = pd.to_datetime(csv['TIMESTAMP'], errors = 'coerce')
                    csv.drop_duplicates('TIMESTAMP', keep = False, inplace = True)
                    csv.set_index('TIMESTAMP', inplace = True)
                    csv = csv[csv.index.day == day] #In case the file has data from another day

                    # Elimino las líneas blancas/vacías
                    csv.dropna(how='all', inplace = True)

                    rawdata = rawdata.append(csv)

                except Exception as e:

                    csv = pd.read_csv(dir_csv + csv_,sep = ',', header = None, na_values = 'NAN',
                                      skip_blank_lines = True, error_bad_lines = False,
                                      warn_bad_lines = True, low_memory = True)

                    if self.database == 'Raw':
                        columns = ['TIMESTAMP', 'RECORD', 'Ux', 'Uy', 'Uz', 'T_SONIC', 'diag_sonic',
                                   'CO2_density', 'CO2_density_fast_tmpr', 'H2O_density', 'diag_irga',
                                   'T_SONIC_corr', 'TA_1_1_1','PA', 'CO2_sig_strgth', 'H2O_sig_strgth']

                    elif self.database == 'Flux':
                        columns = ["TIMESTAMP","RECORD","FC_mass","FC_QC","FC_samples","LE","LE_QC","LE_samples",
                                    "H","H_QC","H_samples","NETRAD","Bowen_ratio","TAU","TAU_QC","USTAR",
                                    "TSTAR","TKE","TA_1_1_1","RH_1_1_1","T_DP_1_1_1","amb_e","amb_e_sat",
                                    "TA_2_1_1","RH_2_1_1","T_DP_2_1_1","e","e_sat","TA_3_1_1","RH_3_1_1",
                                    "T_DP_3_1_1","e_probe","e_sat_probe","H2O_probe","PA","VPD","Ux","Ux_SIGMA",
                                    "Uy","Uy_SIGMA","Uz","Uz_SIGMA","T_SONIC","T_SONIC_SIGMA","sonic_azimuth",
                                    "WS","WS_RSLT","WD_SONIC","WD_SIGMA","WD","WS_MAX","CO2_density",
                                    "CO2_density_SIGMA","H2O_density","H2O_density_SIGMA","CO2_sig_strgth_Min",
                                    "H2O_sig_strgth_Min","NETRAD_meas","sun_azimuth","sun_elevation","hour_angle",
                                    "sun_declination","air_mass_coeff","daytime","FETCH_MAX","FETCH_90",
                                    "FETCH_55","FETCH_40","UPWND_DIST_INTRST","FP_DIST_INTRST","FP_EQUATION"]

                    csv.columns = columns

                    #Replace missing with nan
                    csv.replace(-99999.,np.NaN, inplace = True)

                    #Organize and clean DataFrame
                    csv.set_index('TIMESTAMP', inplace = True)
                    csv.index = pd.to_datetime(csv.index, errors = 'coerce')
                    csv = csv.loc[csv.index.drop_duplicates(keep = False), :]
                    csv = csv[csv.index.day == day]

                    # Elimino las líneas blancas/vacías
                    csv.dropna(how = 'all', inplace = True)

                    rawdata = rawdata.append(csv)
                    print('OJO! Hay problemas con el archivo {}, revisarlo, por {}'.format(csv_, e))

                if (self.type_v == 'anomalies'):
                    anomaly = csv-csv.groupby(pd.Grouper(freq='30min')).transform('mean')
                    anomalies = anomalies.append(anomaly)
                    print('Se entregan las anomalías de los datos, con covarianza de eddy y tiempo de promediado de 30min')


        if self.type_v == 'anomalies':
            return anomalies
        else:
            return rawdata


    def graph_TimeSerie(self, data = None, variables = None,kind = 'line', ylabel = None, name_graph = None,
                        pos_legend = 'top_left', time_units = None, show_figure = True):

        '''
        Input:
            - data : DataFrame containing the time series
            - variables: List of variables to graph. If more than one variable is
              passed, they are graphed in the same space.
            - units: Variable units list
            - name_graph: Title that will have the graph
            - pos_legend: Default is top_left
            - time_units: Graph time units
            - show: Default is True to plot de graph
            - ylabel:

        Output:

            Returns a HTML graph of the given variables
        '''
        from bokeh.palettes import Colorblind8

        if data is None:
            data = self.data

        colormap = Colorblind8[-len(variables):]

        if time_units is not None:
            x_label = 'Time ['+time_units+']'
        else:
            x_label = 'Time'

        serie = data[variables]
        fig_serie = serie.plot_bokeh(kind = kind, rangetool = True, title = name_graph,
                                        ylabel = ylabel,xlabel = x_label, figsize = [600, 200],
                                        colormap = colormap, line_width = 2, legend = pos_legend,
                                        show_figure=show_figure)

        return fig_serie

    def graph_AllVariables(self, show_plot = True):
        '''
        Returns a HTML graph of the variables that the sensor measures.
        If the database is Flux, it also gives a graph of the flows
        '''

        if self.database == 'Raw':

            fig_ux_uy = self.graph_TimeSerie(self.data, ['Ux','Uy'],ylabel = 'm/s',name_graph = 'Time Serie - Horizontal Velocity'
                                            ,show_figure = False)
            fig_uz = self.graph_TimeSerie(self.data, ['Uz'],ylabel = 'm/s',name_graph = 'Time Serie - Vertical Velocity'
            , show_figure = False)
            fig_temp = self.graph_TimeSerie(self.data, ['T_SONIC'],ylabel = '°C',name_graph = 'Time Serie - Temperature'
            ,show_figure = False)
            fig_c02 = self.graph_TimeSerie(self.data, ['CO2_density'],ylabel = 'mg/m³',name_graph = 'Time Serie - CO2 Density'
             ,show_figure = False)
            fig_h20 = self.graph_TimeSerie(self.data, ['H2O_density'],ylabel = 'g/m³',name_graph = 'Time Serie - H2O Density'
             ,show_figure = False)
            fig_p = self.graph_TimeSerie(self.data, ['PA'], ylabel = 'kPa',name_graph = 'Time Serie - Pressure'
             ,show_figure = False)

            tab1 = Panel(child = fig_ux_uy, title = 'Horizontal velocity')
            tab2 = Panel(child = fig_uz, title = 'Vertical velocity')
            tab3 = Panel(child = fig_temp, title = 'Sonic temperature')
            tab4 = Panel(child = fig_c02, title = 'CO₂ density')
            tab5 = Panel(child = fig_h20, title = 'H₂O density')
            tab6 = Panel(child = fig_p, title = 'Atmospheric pressure')

            fig = pandas_bokeh.plot_grid([[Tabs(tabs = [tab1, tab2, tab3, tab4, tab5, tab6])]],
                                         merge_tools = True,toolbar_location = 'left', show_plot=show_plot)

        elif self.database == 'Flux':
            fig_ux_uy = self.graph_TimeSerie(self.data, ['Ux','Uy'],ylabel = 'm/s', show_figure = False)
            fig_uz = self.graph_TimeSerie(self.data, ['Uz'],ylabel = 'm/s', show_figure = False)
            fig_temp = self.graph_TimeSerie(self.data, ['T_SONIC'],ylabel = '°C', show_figure = False)
            fig_c02 = self.graph_TimeSerie(self.data, ['CO2_density'],ylabel = 'mg/m³', show_figure = False)
            fig_h20 = self.graph_TimeSerie(self.data, ['H2O_density'],ylabel = 'g/m³', show_figure = False)
            fig_p = self.graph_TimeSerie(self.data, ['PA'], ylabel = 'kPa', show_figure = False)


            tab1 = Panel(child = fig_ux_uy, title = 'Horizontal velocity')
            tab2 = Panel(child = fig_uz, title = 'Vertical velocity')
            tab3 = Panel(child = fig_temp, title = 'Sonic temperature')
            tab4 = Panel(child = fig_c02, title = 'CO₂')
            tab5 = Panel(child = fig_h20, title = 'H₂O')
            tab6 = Panel(child = fig_p, title = 'Atmospheric pressure')

            fig_LE = self.graph_TimeSerie(self.data, ['LE'], ylabel = 'W/m²', show_figure = False)
            fig_H = self.graph_TimeSerie(self.data, ['H'], ylabel = 'W/m2', show_figure = False)
            fig_TAU = self.graph_TimeSerie(self.data, ['TAU'], ylabel = 'kg/ms²', show_figure = False)

            tab7 = Panel(child = fig_LE, title = 'Latent Heat Flux ')
            tab8 = Panel(child = fig_H, title = 'Sensible Heat Flux')
            tab9 = Panel(child = fig_TAU, title = 'Momentum Flux')

            fig = pandas_bokeh.plot_grid([[Tabs(tabs = [tab1, tab2, tab3, tab4, tab5, tab6])],
                                         [Tabs(tabs = [tab7, tab8, tab9])]],
                                         merge_tools = True,toolbar_location = 'left', show_plot=show_plot)

        return fig


    def anomalies_mean_movile(self, variables = ['LE', 'H', 'TAU'], period = '1H',
                              units = ['W/m²', 'W/m²', 'N/m²'], width = 3, min_periods = 2,
                              show_figure = True,data = None):

        '''
        The database is resampled according to the 'period' parameter.
        The moving average is then calculated by taking a width window 'width' with a
        minimum of 'min_periods' data.
        Anomalies are calculated as
                anomaly = (resampled data) - (moving average)

        Input:
            - variables: List with variables of interest for anomalies. Default is
              turbulent flows
            - period: Used for resampling the database. Default is '1H'
            - units: List of units of the variables of interest.
            - width: Integer with the data number for the mobile window. Default is 3
            - min_periods: Minimum number of data to make the moving average.
              Default is 2
            - data: By default it is the data of the object. It must be a DataFrame
                    with the type DatetimeIndex, and columns with variable names

        Output:
            - An HTML image with the anomalies as bars starting from the value of the
              moving average. Anomalies can be turned off by clicking on the legends.

            - DataFrame with the data used for the graph
          '''
        from bokeh.layouts import row, column, gridplot
        from bokeh.models.widgets import Tabs, Panel
        from bokeh.models import ColumnDataSource, HoverTool, Legend
        from bokeh.plotting import figure, show

        if data is None:
            data = self.data.copy()

        if len(data) == 0:
                print('entre en el if')
                now = datetime.now()
                date_str1 = now.strftime('%Y-%m-%d')
                date_str = now.strftime('%Y-%m-%d %H:%M')
                temp_index = pd.date_range(start=date_str1, end=date_str, freq = '5T')
                data = pd.DataFrame(columns=data.columns, index=temp_index)
                data.replace(to_replace=np.nan, value=0, inplace=True)
                data.index.name = 'TIMESTAMP'


#         COMO SE HACE PARA REDEFINIR VRIABLES DE LA CLASE DENTRO DE ELLA MISMA
        if self.days < 2:
            print('La gráfica puede verse distorsionada porque son pocos datos')
#             question = input('Desea obtener un nuevo conjunto de datos?: ')
#             if question.lower() == 'si':
#                 new_range = input('Ingrese un nuevo valor entero para los días: ')
#                 self.days = new_range
#                 self.data = self.__database()
#             else: pass

        mean = data[variables].resample(period).mean() #Remuestreo al periodo de interés
        mean_movil = mean.rolling(window = width, min_periods = min_periods).mean()
        anom = mean - mean_movil

        pos_anom = mean[anom > 0]
        neg_anom = mean[anom < 0]

        mean = mean.join(pos_anom, how = 'left', rsuffix = 'pos').join(neg_anom,
         how = 'left', rsuffix = 'neg')
        mean = mean.join(mean_movil, how = 'left', rsuffix = 'mm').join(anom,
         how = 'left', rsuffix = 'anom')
        source = ColumnDataSource(mean)

        time = anom.index[1]-anom.index[0]
        figures = {}
        tabs_ = []
        for variable, units in zip(variables, units):
            p = figure(plot_width=800, plot_height=350, x_axis_type="datetime",
                       tools=['pan', 'save', 'reset'], toolbar_location = "right")

            pos = p.vbar(x = 'TIMESTAMP', top = variable+'pos', bottom = variable+'mm',
                        source=source, width = time, fill_color = 'darkmagenta',
                         fill_alpha = 0.5, line_color = 'white', name = 'Pos')

            neg = p.vbar(x = 'TIMESTAMP', top = variable+'neg', bottom = variable+'mm',
                       source=source, width = time, fill_color = 'yellow',fill_alpha = 0.5,
                       line_color = 'white', name = 'Neg')

            mm = p.line(x = 'TIMESTAMP', y = variable+'mm', source = source, name = 'Mean',
                       line_width = 4, color = 'gray')

            #Custom toolbar
            p.toolbar.autohide = True

            #Add tool HoverTool
            hover = HoverTool(mode = 'mouse')
            hover.tooltips = [
                              ('Anomaly', "@"+variable+'anom{0.000}'),
                              ('Moving average', "@"+variable+'mm{0.000}')]
#             ('Date', '@TIMESTAMP{%F}')
            hover.formatters = {'@TIMESTAMP': 'datetime'}
            p.add_tools(hover)

            #Custom legend
            legend = Legend(items = [('Positive anomaly', [pos]),
                                     ('Negative anomaly',[neg]),
                                     ('Mean', [mm])],
                            location = "center", orientation = 'horizontal',
                            border_line_color = 'gray')
            p.add_layout(legend, 'above')
            p.legend.label_standoff = 0
            p.legend.glyph_width = 10
            p.legend.spacing = 0
            p.legend.padding = 5
            p.legend.margin = 2

            #Custom axes and axis
            p.xgrid.grid_line_color = None
            p.ygrid.grid_line_color = None
            p.legend.click_policy="hide"
            p.xaxis.axis_label = "Time [Hours]".format(width)
            p.yaxis.axis_label = variable
            if units is not None:
                p.yaxis.axis_label = variable +' ['+ units+']'
            p.yaxis.major_label_orientation = "vertical"
            p.outline_line_color = 'white'

            #Tabs
            tab = Panel(child = p, title = variable)
            tabs_.append(tab)
#             show(p)
        tabs = Tabs(tabs = tabs_)
        print('You can clik in legend to hide any item')
        if show_figure == True:
            show(tabs)

        return mean, tabs

    def Bokeh_TimeSerie(self):

        data = self.data.copy()

        if len(data) == 0:
                print('entre en el if')
                now = datetime.now()
                date_str1 = now.strftime('%Y-%m-%d')
                date_str = now.strftime('%Y-%m-%d %H:%M')
                temp_index = pd.date_range(start=date_str1, end=date_str, freq = '5T')
                data = pd.DataFrame(columns=data.columns, index=temp_index)
                data.replace(to_replace=np.nan, value=0, inplace=True)

        if self.database == 'Flux':

            col_bowen = ' '.join('Bowen_ratio'.split('_'))

            data.rename(columns = {'LE_QC': 'LE QC', 'H_QC': 'H QC', 'TAU_QC': 'Momentum QC',\
                                        'Bowen_ratio': col_bowen,'TAU': 'Momentum flux', \
                                        'USTAR': 'Friction velocity', 'TSTAR': 'Scaling temperature',\
                                        'WS': 'Wind Speed', 'WS_MAX': 'Maximum WS'},
                            inplace=True)

            variables = ['LE', 'H', col_bowen, 'Momentum flux', 'Friction velocity', 'Scaling temperature', 'TKE',\
            ['Wind Speed', 'Maximum WS'],'LE QC','H QC', 'Momentum QC']
            names = ['Time serie - Latent heat flux', 'Time serie - Sensible heat flux', 'Time serie - Bowen ration',\
            'Time serie - Momentum flux', 'Time serie - Friction velocity', 'Time serie - Scaling temperature',\
            'Time serie - Turbulence kinetic energy', 'Time serie - Average wind speed', 'Time serie: Overall quality grade - LE','Time serie: Overall quality grade - H',\
            'Time serie: Overall quality grade - Momentum']
            ylabels = ['W/m2'.translate(SUP), 'W/m2'.translate(SUP), ' '.translate(SUP), 'kg/m1/s2'.translate(SUP),\
            'm/s', '°C', 'm2/s2'.translate(SUP),'m/s',' ', ' ', ' ']
            titles = ['LE', 'H', col_bowen, 'TAU', 'USTAR', 'TSTAR', 'TKE', 'WS', 'LE QC', 'H QC', 'TAU QC']

            tabs_ = []

            for variable, name, ylabel, title in zip(variables, names, ylabels, titles):
                if isinstance(variable,list):
                    fig = self.graph_TimeSerie(data = data, variables = variable, name_graph = name,
                                    ylabel = ylabel, show_figure = False)
                else:
                    if variable.endswith('QC'):
                        kind = 'step'
                    else:
                        kind = 'line'
                    fig = self.graph_TimeSerie(data = data, variables = [variable], name_graph = name,
                                        ylabel = ylabel, kind = kind, show_figure = False)
                tab = Panel(child = fig, title = title)
                tabs_.append(tab)

            order_flux = pandas_bokeh.plot_grid([[Tabs(tabs = tabs_[8:])],
                                             [Tabs(tabs = tabs_[0:3]), Tabs(tabs = tabs_[3:8])]
                                            ], merge_tools = True, toolbar_location = 'left')

            return order_flux

        elif self.database == 'Raw':

            fig_all_variables = self.graph_AllVariables(show_plot = False)

            variables = ['diag_sonic', 'diag_irga', 'H2O_sig_strgth', 'CO2_sig_strgth']
            names = ['Diagnostic SONIC', 'Diagnostic '+' '.join(self.name.upper().split('_')),\
            ' '.join('H2O_sig_strgth'.translate(SUB).split('_')), ' '.join('CO2_sig_strgth'.translate(SUB).split('_'))]
            ylabels = [' ', ' ', ' ', ' ']
            titles = ['Diag Sonic', 'Diag Irgason', 'Diag H20'.translate(SUB), 'Diag CO2'.translate(SUB)]

            tabs_ =[]
            for variable, name, ylabel, title in zip(variables, names, ylabels, titles):
                fig = self.graph_TimeSerie(data = data, variables = [variable], name_graph = name,
                                    ylabel = ylabel, kind = 'step', show_figure = False)
                tab = Panel(child = fig, title = title)
                tabs_.append(tab)


            order_TS = pandas_bokeh.plot_grid([[Tabs(tabs = tabs_),
                                                fig_all_variables]],
                                              merge_tools = True, toolbar_location = 'left')

            return order_TS

    def Bokeh_HeatMap_Percent(self):
        from bokeh.models import BasicTicker, ColorBar, LinearColorMapper, PrintfTickFormatter, Range1d
        if self.database == 'Raw':
            csv = self.data.copy()

            #Cargo y configuro el archivo con los registros de meses-dias anteriores
            csv_records = '/home/complex/JupyterNotebooks/web_site/csv_HeatMap/'+self.name.upper()+'_%records.csv'
            data = pd.read_csv(csv_records, sep = ',', header = [0], index_col = 0)
            col1 = list('2019-'+str(m) for m in range(12,13))
            col2 = list('2020-'+str(m) for m in range(1,13))
            columnas = col1 + col2
            data.columns = columnas

            #Indices del df-data y almaceno la informacion en data
            año, mes, dia = self.__path_files[0].split('_')[2].split('.')[0].split('-')
            data.loc[int(dia), año+'-'+str(int(mes))] = len(csv.index)/(24*60*60*20)*100

            #Termino de organizar los titulos de las columnas del df
            col = ['2019-Dec', '2020-Jan', '2020-Feb', '2020-Mar', '2020-Apr', '2020-May', '2020-Jun', '2020-Jul', '2020-Aug',
                   '2020-Sep', '2020-Oct', '2020-Nov', '2020-Dec']
            data.columns = col
            data.columns.name = 'Mes'
            data = round(data.astype(float), 1)
            data.to_csv(csv_records, sep = ',', na_rep = 'NAN')

            #Convierto df a columna
            data_ = pd.DataFrame(data.stack(), columns = ['percent']).reset_index()
            day = ['      '+str(day) for day in data.index]

            #Control de colores para el heatmap
            colors = ["#C0C0C0", "#FF0000", "#FF4500", "#FFA500", "#FFD700", "#FFFF00", "#ADFF2F", '#7CFC00', "#008000",
                      "#006400"]
            mapper = LinearColorMapper(palette = colors, low = data_.percent.min(), high = data_.percent.max())

            #Herramientas para interactuar con la gráfica
            TOOLS = "hover,save,pan,box_zoom,reset,wheel_zoom"

            #Generación de gráfico
            p = figure(title = 'Monitoring station '+' '.join(self.name.split('_'))+': Data recording',
                       x_range = list(day), y_range = list(reversed(col)),
                       x_axis_location = 'above', plot_width = 800, plot_height = 350,
                       tools = TOOLS, toolbar_location = 'below',
                       tooltips=[('Date', '@Mes @Dia'), ('Percent', '@percent%')])

            #Control de gráfico
            p.grid.grid_line_color = None
            p.ygrid.grid_line_color = 'gainsboro'
            #p.axis.axis_line_color = None
            p.axis.major_label_text_font_size = "12px"
            p.xaxis.axis_label = 'Days'
            p.yaxis.axis_label = 'Year - Month'

            #Generación de rectanculos
            p.rect(x = "Dia", y = "Mes", width = .9, height = .9, source = data_,
                   fill_color={'field': 'percent', 'transform': mapper}, line_color=None)

            #Generación de barra de color
            color_bar = ColorBar(color_mapper = mapper, major_label_text_font_size = "12px",
                                 ticker = BasicTicker(desired_num_ticks = len(colors)),
                                 formatter = PrintfTickFormatter(format="%d%%"),
                                 label_standoff = 10, border_line_color = None, location = (0, 0))
            p.add_layout(color_bar, 'right')

            return p
        else:
            'El registro de datos solo está disponible para la base de datos crudos'

    def fig_html(self, lst_fig):

        """ Entradas:
        import numpy as npIRGAS
        ON_name --> str, Nombre de la carpeta de las estaciones IRGASON:
            [
            IRGASON_Candelaria,
            IRGASON_Federico_Carrasquilla,
            IRGASON_SENA,
            IRGASON_CASD_10M,
            IRGASON_ITM,
            IRGASON_Villa_Niza,
            IRGASON_CASD_20M,
            IRGASON_Jesus_Maria_Valle,
            IRGASON_Villa_Socorro,
            IRGASON_CASD_30M
            ]
        lst_fig --> list, lista con todas las figuras a renderizar en el html
        """

        # Almaceno las figuras
        fig = lst_fig

        # Extraigo los scripts y div de fig para crear el archivo html
        script, div = components(fig)

        # Creo el html con todas las figuras
        irg_name = ' '.join(self.name.split('_'))
        template = Template(
            '''<!DOCTYPE html>
            <html lang="en">
                <head>
                    <meta charset="utf-8">
                    <title> {{irg_name}} </title>
                    {{ js_resources }}
                    {{ css_resources }}
                    {{ script }}
                </head>
                <h1>

                Monitoring Station {{ irg_name }}

                </h1>
                <body>
                    {% for key in div %}

                        {{ key }}

                    {% endfor %}
                </body>
            </html>
            '''
        )

        js_resources = INLINE.render_js()
        css_resources = INLINE.render_css()

        filename = '/home/complex/JupyterNotebooks/web_site/figures/'+self.name.upper()+'.html'

        html = template.render(js_resources = js_resources,
                               css_resources = css_resources,
                               script = script,
                               irg_name = irg_name,
                               div = div)

        with open(filename, 'w') as f:
            f.write(html)


import sys
sys.path.append('../')
import time
import Turbulence as tbl

def Bokeh_Fig_WebCOMPLEX(IRGASON_name):


    """ Entradas:
    import numpy as npIRGAS
    ON_name --> str, Nombre de la carpeta de las estaciones IRGASON:
        [
        IRGASON_Candelaria,
        IRGASON_Federico_Carrasquilla,
        IRGASON_SENA,
        IRGASON_CASD_10M,
        IRGASON_ITM,
        IRGASON_Villa_Niza,
        IRGASON_CASD_20M,
        IRGASON_Jesus_Maria_Valle,
        IRGASON_Villa_Socorro,
        IRGASON_CASD_30M
        ]
    ndays_back --> int, son el número de días hacia atras, contando desde el hoy, para realizar la gráfica
    """

    #Contabilizo el tiempo de ejecución
    start_time = time.time()

    sensor_h = tbl.Sensor(database='Raw', name= IRGASON_name, days=1)

    sensor_time_raw = tbl.Sensor(database='Raw', name = IRGASON_name, days=3, Temp_resolution = '1T')

    sensor_time_flux = tbl.Sensor(database='Flux', name = IRGASON_name, days=3)

    fig_flux = sensor_time_flux.Bokeh_TimeSerie()
    fig_ts = sensor_time_raw.Bokeh_TimeSerie()
    fig_hm = sensor_h.Bokeh_HeatMap_Percent()
    datos, fig_anm = sensor_time_flux.anomalies_mean_movile()

    # Almaceno las figuras
    lst_figs = [fig_hm, fig_ts,fig_anm,fig_flux]

    # Creo un archivo html con todas las figuras
    sensor_h.fig_html(lst_figs)

    m = print('El código se demora {} minutos en ejecutarse'.format(round((time.time() - start_time)/60., 2)))

    return m



Bokeh_Fig_WebCOMPLEX('IRGASON_CASD_10M')
Bokeh_Fig_WebCOMPLEX('IRGASON_CASD_20M')
Bokeh_Fig_WebCOMPLEX('IRGASON_CASD_30M')
Bokeh_Fig_WebCOMPLEX('IRGASON_Candelaria')
Bokeh_Fig_WebCOMPLEX('IRGASON_ITM')
Bokeh_Fig_WebCOMPLEX('IRGASON_Jesus_Maria_Valle')
Bokeh_Fig_WebCOMPLEX('IRGASON_Villa_Socorro')
Bokeh_Fig_WebCOMPLEX('IRGASON_Villa_Niza')
Bokeh_Fig_WebCOMPLEX('IRGASON_Federico_Carrasquilla')
Bokeh_Fig_WebCOMPLEX('IRGASON_SENA')
