# 6. Технологический ландшафт ML-архитектур

Технологический стек ML-приложений многослоен: от языков и библиотек до
оркестраторов пайплайнов и облачных платформ. Ниже приведён обзор основных
категорий с перечислением конкретных систем, фреймворков и библиотек,
используемых в каждой из них.

## Языки и экосистемы

В ML доминирует **Python** благодаря экосистеме библиотек для данных и обучения;
для распределённой обработки и интеграции с корпоративным стеком широко
используются **JVM-языки** (**Scala**, **Java**, **Kotlin**). **R** применяется
в аналитике и исследованиях. Для высоконагруженного инференса и инфраструктуры —
**Go**, **Rust**, **C++**; для научных расчётов — **Julia**.

Конкретные технологии:

- **Языки**: Python, Scala, Java, Kotlin, R, Go, Rust, C++, Julia.
- **Библиотеки экосистемы Python**: NumPy, Pandas, SciPy, Matplotlib, Seaborn,
  Polars.
- **JVM**: Breeze, ND4J, Deeplearning4j, Apache Spark (Scala/Java API).

## Фреймворки обучения и инференса

Фреймворки глубокого обучения обеспечивают построение и обучение нейросетей;
библиотеки классического ML — задачи без глубоких архитектур; инструменты
инференса — развёртывание моделей с низкой задержкой.

Конкретные технологии:

- **Глубокое обучение**: TensorFlow, Keras, PyTorch, JAX, MXNet, PaddlePaddle,
  ONNX (формат обмена моделями).
- **Классический ML**: scikit-learn, XGBoost, LightGBM, CatBoost, statsmodels,
  H2O.
- **Сервинг и инференс**: TensorFlow Serving, TorchServe, ONNX Runtime, NVIDIA
  Triton Inference Server, OpenVINO, TensorRT, TensorFlow Lite, PyTorch Mobile,
  Apple Core ML.

## Обработка и хранение данных

Распределённые фреймворки используются для пайплайнов подготовки данных и
признаков; хранилища — для долговременного хранения и аналитики; системы
потоковой доставки — для real-time обновления признаков и онлайнового обучения.

Конкретные технологии:

- **Обработка данных (batch/stream)**: Apache Spark, Apache Flink, Apache Beam,
  Dask, Ray, Polars, DuckDB.
- **Хранилища (data lake, warehouse)**: Apache Hadoop (HDFS), Amazon S3, MinIO,
  Delta Lake, Apache Iceberg, Snowflake, Google BigQuery, Amazon Redshift,
  Apache Hive, Databricks.
- **Потоковая доставка событий**: Apache Kafka, Apache Pulsar, Amazon Kinesis,
  Google Cloud Pub/Sub, Redis Streams.

## Оркестрация и управление пайплайнами

Оркестраторы исполняют графы задач (данные → признаки → обучение → выкат);
системы экспериментов хранят конфигурации и метрики; реестры моделей — версии
моделей и их статусы.

Конкретные технологии:

- **Оркестраторы задач**: Apache Airflow, Kubeflow Pipelines, Prefect, Dagster,
  Luigi, Argo Workflows, Metaflow.
- **Управление экспериментами**: MLflow, Weights & Biases (W&B), Neptune.ai,
  Comet, Sacred.
- **Реестры моделей и версионирование**: MLflow Model Registry, Kubeflow, DVC
  (Data Version Control), Verta.

## Сервинг моделей и онлайн-инференс

Серверы моделей разворачивают модели как HTTP/gRPC-сервисы; библиотеки
встроенного инференса — для edge и мобильных устройств; шлюзы — для
маршрутизации и политик доступа.

Конкретные технологии:

- **Серверы моделей**: TensorFlow Serving, TorchServe, KServe (Kubernetes),
  Seldon Core, BentoML, Cortex, NVIDIA Triton Inference Server, Ray Serve.
- **Встроенный инференс**: ONNX Runtime, TensorFlow Lite, LibTorch, OpenVINO,
  TensorRT.
- **Шлюзы и маршрутизация**: Kong, Envoy, кастомные API Gateway поверх
  Kubernetes Ingress или сервисной сетки.

## Облачные ML-платформы и управляемые сервисы

Облачные платформы предоставляют управляемые среды для обучения, инференса и
MLOps; вертикальные решения — готовые сервисы под конкретные домены (речь,
текст, диалоги).

Конкретные технологии:

- **Облачные ML-платформы**: Amazon SageMaker, Google Vertex AI, Azure Machine
  Learning, Yandex DataSphere, Databricks, IBM Watson Studio.
- **Управляемый инференс и API моделей**: AWS SageMaker Endpoints, Google Vertex
  AI Prediction, Azure ML Endpoints, OpenAI API, Anthropic API, референсные
  развёртытия открытых LLM (vLLM, TGI).
- **Вертикальные и AI-сервисы**: диалоговые платформы (Dialogflow, Amazon Lex,
  Rasa), сервисы распознавания речи (Whisper, облачные ASR), готовые RAG/поиск
  (Amazon Kendra, Google Enterprise Search).

## Векторные и специализированные хранилища

Векторные БД и индексы — основа семантического поиска и RAG; расширения СУБД и
гибридный поиск дополняют классический полнотекстовый поиск.

Конкретные технологии:

- **Векторные БД и индексы**: Pinecone, Weaviate, Milvus, Qdrant, Chroma,
  pgvector (PostgreSQL), Elasticsearch с dense vectors, Faiss, Annoy.
- **Расширения СУБД**: pgvector, ClickHouse (embeddings), Redis Stack (vector
  search).
- **Полнотекстовый и гибридный поиск**: Elasticsearch, OpenSearch, Apache Solr,
  Vespa.

## Инфраструктура и эксплуатация

Контейнеры и оркестрация обеспечивают развёртывание моделей и пайплайнов;
сервисная сеть и мониторинг — отказоустойчивость и наблюдаемость ML-контуров.

Конкретные технологии:

- **Контейнеризация и оркестрация**: Docker, containerd, Kubernetes, Helm,
  Kustomize.
- **Сервисная сеть и сетевой слой**: Istio, Linkerd, Envoy, Consul.
- **Мониторинг и логирование**: Prometheus, Grafana, OpenTelemetry, ELK/OpenSearch
  Stack, Datadog, Evidently (мониторинг качества ML), WhyLabs.

## Связь технологий с архитектурными концепциями

Перечисленные технологии реализуют принципы из разделов 1–5. Жизненный цикл
модели и разделение контуров материализуются в фреймворках обработки данных
(Spark, Flink), оркестраторах (Airflow, Kubeflow), реестрах (MLflow). MLOps-
практики — в тех же оркестраторах, системах экспериментов (MLflow, W&B) и
облачных платформах (SageMaker, Vertex AI). Диалоговые системы и распознавание
намерений опираются на сервинг (TorchServe, KServe), API-шлюзы и трассировку
(OpenTelemetry). RAG — на векторные хранилища (Pinecone, Weaviate, pgvector),
пайплайны индексации и генеративные API. Выбор конкретных инструментов
определяется нефункциональными требованиями и ограничениями организации.
