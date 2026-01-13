import joblib
import os
import numpy as np

# Путь к твоей модели
MODEL_PATH = os.path.join(os.path.dirname(__file__), "logistics_risk_model.pkl")

# Загружаем модель один раз при импорте
model = joblib.load(MODEL_PATH)


def predict_risk(distance: float, cargo_type: int, driver_exp: int, hour: int, weather: int):
    # Подготавливаем данные для модели (должны быть в том же порядке, что при обучении)
    input_data = np.array([[distance, cargo_type, driver_exp, hour, weather]])

    # Делаем предсказание (получим 0, 1 или 2)
    prediction = int(model.predict(input_data)[0])

    # Маппинг для фронтенда (как в Figma)
    risk_map = {0: "Low", 1: "Medium", 2: "High"}

    return prediction, risk_map.get(prediction)


if __name__ == "__main__":
    # Пробный запуск: Дистанция 1000км, тип 2, опыт 1 год, время 23:00, погода 1
    p_class, p_level = predict_risk(1000, 2, 1, 23, 1)
    print(f"Класс: {p_class}, Уровень: {p_level}")