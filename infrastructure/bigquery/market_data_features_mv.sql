-- CREATE OR REPLACEで冪等性を担保
CREATE OR REPLACE MATERIALIZED VIEW `${PROJECT_ID}.${BQ_DATASET_NAME}.${BQ_FEATURES_MV_NAME}`
PARTITION BY DATE(timestamp)
CLUSTER BY symbol
OPTIONS(
  enable_refresh = true,
  refresh_interval_minutes = 60 -- 60分ごとに自動リフレッシュ（コストと鮮度のバランス）
)
AS
SELECT
  *,
  -- 将来の分析のために複数の移動平均を事前計算
  AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS sma_10,
  AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20,
  AVG(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma_50,
  STDDEV(close) OVER (PARTITION BY symbol ORDER BY timestamp ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS volatility_20
FROM
  `${PROJECT_ID}.${BQ_DATASET_NAME}.market_data_history`;
