from ML.classifier.preprocessor import clean_email_text
import joblib
import pickle
import os


class EmailClassifier:
    def __init__(self, model_dir=None):
        if model_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            model_dir = os.path.join(project_root, "ML", "models")

        model_dir = os.path.expanduser(model_dir)

        print(f"🔄 Загружаю модели из: {model_dir}")

        model_path = os.path.join(model_dir, "model.pkl")
        vectorizer_path = os.path.join(model_dir, "vectorizer.pkl")
        label_encoder_path = os.path.join(model_dir, "label_encoder.pkl")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Модель не найдена: {model_path}")
        if not os.path.exists(vectorizer_path):
            raise FileNotFoundError(f"Векторизатор не найден: {vectorizer_path}")
        if not os.path.exists(label_encoder_path):
            raise FileNotFoundError(f"Label encoder не найден: {label_encoder_path}")

        self.model = joblib.load(model_path)
        with open(vectorizer_path, 'rb') as f:
            self.vectorizer = pickle.load(f)
        with open(label_encoder_path, 'rb') as f:
            self.label_encoder = pickle.load(f)

        print(f"✅ Модели загружены. Доступные категории: {list(self.label_encoder.classes_)}")

    def predict(self, email_text):
        clean_text = clean_email_text(email_text)

        features = self.vectorizer.transform([clean_text])

        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]

        category = self.label_encoder.inverse_transform([prediction])[0]

        prob_dict = {}
        for i, cat in enumerate(self.label_encoder.classes_):
            prob_dict[cat] = float(probabilities[i])

        return {
            'category': category,
            'confidence': float(probabilities[prediction]),
            'probabilities': prob_dict,
            'clean_text': clean_text[:100] + "..." if len(clean_text) > 100 else clean_text
        }

    def batch_predict(self, email_texts):
        """Предсказание для списка писем"""
        return [self.predict(text) for text in email_texts]