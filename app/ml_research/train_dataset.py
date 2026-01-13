import pandas as pd
import numpy as np

# Количество строк (можешь увеличить, если нужно больше данных)
n_samples = 5000
np.random.seed(42)

# 1. Генерация признаков (Features)
data = {
    'distance': np.random.uniform(10, 2000, n_samples).round(2),  # Расстояние в км
    'cargo_type': np.random.choice([0, 1, 2], n_samples, p=[0.6, 0.25, 0.15]),  # 0-стандарт, 1-хрупкий, 2-ценный
    'driver_exp': np.random.randint(0, 240, n_samples),  # Опыт в месяцах (0-20 лет)
    'hour_of_day': np.random.randint(0, 24, n_samples),  # Час суток
    'is_weather_bad': np.random.choice([0, 1], n_samples, p=[0.8, 0.2])  # 0-ясно, 1-плохо
}

df = pd.DataFrame(data)


# 2. Логика расчета целевой переменной (Risk Score)
# Мы создаем зависимость, которую модель должна будет выучить
def calculate_risk(row):
    score = 10  # Базовый риск
    score += (row['distance'] / 2000) * 35  # Расстояние дает до 35 баллов
    if row['cargo_type'] == 1: score += 15  # Хрупкий груз
    if row['cargo_type'] == 2: score += 25  # Ценный груз
    score += max(0, 25 - (row['driver_exp'] / 6))  # Малый опыт дает до 25 баллов
    if row['hour_of_day'] >= 22 or row['hour_of_day'] <= 6: score += 15  # Ночь
    if row['is_weather_bad'] == 1: score += 15  # Погода

    # Добавляем случайный шум, чтобы модель не просто зубрила формулу
    score += np.random.normal(0, 4)
    return int(np.clip(score, 0, 100))


df['risk_score'] = df.apply(calculate_risk, axis=1)

# 3. Сохранение в CSV
df.to_csv('logistics_risk_data.csv', index=False)

print("--- Генерация завершена ---")
print(f"Файл 'logistics_risk_data.csv' на {n_samples} строк создан в папке проекта.")
print(df.head())  # Показываем первые 5 строк для проверки