import sweetviz
import pandas as pd
from sklearn.model_selection import train_test_split
import shap
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
import numpy as np
import matplotlib.pyplot as plt
from tpot import TPOTClassifier
from tpot.config import classifier_config_dict

# 数据读取
file_path = "updated_keyword_counts_per_line.csv"
data = pd.read_csv(file_path)

# 数据预处理
missing_values_count = data.isnull().sum()
missing_values_sorted = missing_values_count.sort_values(ascending=False)
total_cells = len(data)
missing_percentage = (missing_values_sorted / total_cells) * 100
missing_data = pd.DataFrame({'Missing Values': missing_values_sorted, 'Percentage (%)': missing_percentage})
print(missing_data)
data = data.dropna()

# Sweetviz分析
report = sweetviz.analyze(data)
report.show_html("report.html")

# 处理名义变量
nominal_columns = ['計罰', '總額預定', '逾期']
label_encoders = {}

for column in nominal_columns:
    le = LabelEncoder()
    data[column] = le.fit_transform(data[column])
    label_encoders[column] = le

# 特征选择
data['Target'] = data['Target'].map({'punitive': 1, 'compensatory': 2, 'notdefine': 0})
y = data["Target"]
x = data.drop("Target", axis=1).drop("id", axis=1)
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

# 随机森林模型训练
rf = RandomForestClassifier(n_estimators=100, random_state=42)
param_grid = {'max_depth': [5, 10, 15], 'min_samples_leaf': [1, 3, 5]}
grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, cv=3, scoring='f1_weighted', verbose=2)
grid_search.fit(x_train, y_train)
best_rf = grid_search.best_estimator_
rf_model = RandomForestClassifier(n_estimators=100, max_depth=15, min_samples_leaf=4, random_state=42)
rf_model.fit(x_train, y_train)
print(rf_model.score(x_train, y_train))
print(rf_model.score(x_test, y_test))

# 特征重要性分析
features = x_train.columns
importances = best_rf.feature_importances_
indices = np.argsort(importances)[::-1]
sorted_features = pd.DataFrame({'Features': features[indices], 'Importance': importances[indices]})

plt.rcParams['font.sans-serif'] = ['Arial']  # 使用Arial字體
plt.rcParams['axes.unicode_minus'] = False    # 解決負號顯示問題
plt.figure(figsize=(10, 6))
plt.title('Feature Importances by RandomForest')
plt.bar(range(len(importances)), importances[indices], color='b', align='center')
plt.xticks(range(len(importances)), features[indices], rotation=90)
plt.xlabel('Relative Importance')
plt.show()

top_features = sorted_features['Features'][:3]
x_train_selected = x_train[top_features]
x_test_selected = x_test[top_features]

# 再次进行GridSearchCV优化
grid_search = GridSearchCV(estimator=rf, param_grid=param_grid, cv=3, scoring='f1_weighted', verbose=2)
grid_search.fit(x_train_selected, y_train)
print(grid_search.best_params_)

# 训练新的随机森林模型
rf_1 = RandomForestClassifier(n_estimators=20, max_depth=6, min_samples_leaf=4, random_state=42)
rf_1.fit(x_train, y_train)
print(rf_1.score(x_train, y_train))
print(rf_1.score(x_test, y_test))

sweetviz.analyze(pd.concat([x_train_selected, y_train], axis=1)).show_html("selected.html")

# TPOT模型训练
xgboost_keys = [key for key in classifier_config_dict if ("xgboost" or "gradientboosting") in key.lower()]
for key in xgboost_keys:
    del classifier_config_dict[key]

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

# 确保输入数据的正确性
print(x_train_selected.shape)
print(y_train.shape)

# 调用TPOT进行模型优化
tpot_new.fit(x_train_selected, y_train)

# 导出TPOT生成的最佳管道
tpot_new.export('tpot_exported_pipeline.py')

# 使用TPOT生成的最佳管道
best_pipeline = tpot_new.fitted_pipeline_

best_pipeline.fit(x_train_selected, y_train)
print(best_pipeline.score(x_train_selected, y_train))
print(best_pipeline.score(x_test_selected, y_test))
