import sweetviz
import pandas as pd
import sklearn as sk
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import tpot
from sklearn.preprocessing import OneHotEncoder
import shap

file_path = "top_20_words_per_line.csv"
data = pd.read_csv(file_path)

"""Data Preprocessing"""

import pandas as pd

missing_values_count = data.isnull().sum()

missing_values_sorted = missing_values_count.sort_values(ascending=False)

total_cells = len(data)
missing_percentage = (missing_values_sorted / total_cells) * 100

missing_data = pd.DataFrame({'Missing Values': missing_values_sorted,
                             'Percentage (%)': missing_percentage})

print(missing_data)

data = data.dropna()

import pandas as pd

missing_values_count = data.isnull().sum()

missing_values_sorted = missing_values_count.sort_values(ascending=False)

total_cells = len(data)
missing_percentage = (missing_values_sorted / total_cells) * 100

missing_data = pd.DataFrame({'Missing Values': missing_values_sorted,
                             'Percentage (%)': missing_percentage})

print(missing_data)

report = sweetviz.analyze(data)
report.show_html("report.html")

data.drop(index=0, inplace=True)

nominal_columns = [
    'Marital status',
    'Application mode',
    'Course',
    'Daytime/evening attendance',
    'Previous qualification',
    'Nacionality',
    'Mother\'s qualification',
    'Father\'s qualification',
    'Mother\'s occupation',
    'Father\'s occupation',
    'Displaced',
    'Educational special needs',
    'Debtor',
    'Tuition fees up to date',
    'Gender',
    'Scholarship holder',
    'International'
]

import pandas as pd

data = pd.get_dummies(data, columns=nominal_columns)

missing_values_count = data.isnull().sum()

missing_values_sorted = missing_values_count.sort_values(ascending=False)

total_cells = len(data)
missing_percentage = (missing_values_sorted / total_cells) * 100

missing_data = pd.DataFrame({'Missing Values': missing_values_sorted,
                             'Percentage (%)': missing_percentage})

print(missing_data)

"""Feature Selection"""

data['Target'].value_counts()

data['Target'] = data['Target'].map({'punitive': 2, 'compensatory': 1, 'notdefine': 0})

y = data["Target"]
x = data.drop("Target", axis = 1)

x_train,x_test,y_train,y_test = train_test_split(x,y,test_size=0.2)

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV

rf = RandomForestClassifier(n_estimators=100, random_state=42)

param_grid = {
    'max_depth': [5, 10, 15],
    'min_samples_leaf': [1, 3, 5]
}
grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, cv=3, scoring='f1_weighted', verbose=2)

grid_search.fit(x_train, y_train)

best_rf = grid_search.best_estimator_

grid_search.best_params_

rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    min_samples_leaf=1,
    random_state=42
)

rf_model.fit(x_train, y_train)

rf_model.score(x_train, y_train)

rf_model.score(x_test, y_test)

rf_model = RandomForestClassifier(
    n_estimators=20,
    max_depth=8,
    min_samples_leaf=5,
    random_state=42
)

rf_model.fit(x_train, y_train)

rf_model.score(x_train, y_train)

rf_model.score(x_test, y_test)

feature_importances = rf_model.feature_importances_

import numpy as np
import matplotlib.pyplot as plt

features = x_train.columns
importances = best_rf.feature_importances_
indices = np.argsort(importances)[::-1]

sorted_features = pd.DataFrame({'Features': features[indices], 'Importance': importances[indices]})

plt.figure(figsize=(10, 6))
plt.title('Feature Importances by RandomForest')
plt.bar(range(len(importances)), importances[indices], color='b', align='center')
plt.xticks(range(len(importances)), features[indices], rotation=90)
plt.xlabel('Relative Importance')
plt.show()

top_features = sorted_features['Features'][:25]
x_train_selected = x_train[top_features]
x_test_selected = x_test[top_features]

grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, cv=3, scoring='f1_weighted', verbose=2)

grid_search.fit(x_train_selected, y_train)

grid_search.best_params_

rf_1 = RandomForestClassifier(
    n_estimators=20,
    max_depth=6,
    min_samples_leaf=1,
    random_state=42
)

rf_1.fit(x_train, y_train)

rf_1.score(x_train, y_train)

rf_1.score(x_test, y_test)

sweetviz.analyze(pd.concat([x_train_selected, y_train], axis=1)).show_html("selected.html")

"""Analyse"""

from tpot.config import classifier_config_dict

xgboost_keys = [key for key in classifier_config_dict if ("xgboost" or "gradientboosting") in key.lower()]
for key in xgboost_keys:
    del classifier_config_dict[key]

from tpot import TPOTClassifier

tpot_new = TPOTClassifier(
    generations=5,
    population_size=50,
    verbosity=2,
    scoring='f1_weighted',
    random_state=42,
    config_dict=classifier_config_dict,
    cv=5,
    n_jobs=-1,
)

tpot_new.fit(x_train_selected, y_train)

tpot_new.export('tpot_exported_pipeline.py')

exported_pipeline = RandomForestClassifier(
    bootstrap=False,
    criterion="gini",
    max_features=0.4,
    min_samples_leaf=4,
    min_samples_split=14,
    n_estimators=100,
    random_state=42
)

exported_pipeline.fit(x_train_selected, y_train)

exported_pipeline.score(x_train_selected, y_train)

exported_pipeline.score(x_test_selected, y_test)

exported_pipeline = RandomForestClassifier(
    bootstrap=False,
    criterion="gini",
    max_features=0.4,
    min_samples_leaf=13,
    min_samples_split=5,
    n_estimators=100,
    random_state=42
)

exported_pipeline.fit(x_train_selected, y_train)

exported_pipeline.score(x_train_selected, y_train)

exported_pipeline.score(x_test_selected, y_test)

"""SHAP"""

explainer = shap.Explainer(exported_pipeline)

shap_values = explainer.shap_values(x_train_selected)

result_dict = {0: 'Graduate', 1: 'Dropout', 'Enrolled': 2}

for i in range(3):
    shap.summary_plot(shap_values[:, :, i], x_train_selected, feature_names=x_train_selected.columns)