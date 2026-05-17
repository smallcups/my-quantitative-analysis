mysqldump: [Warning] Using a password on the command line interface can be insecure.
-- MySQL dump 10.13  Distrib 8.0.29, for Win64 (x86_64)
--
-- Host: localhost    Database: stock_cursor
-- ------------------------------------------------------
-- Server version	8.0.29

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `ml_model_definition`
--

DROP TABLE IF EXISTS `ml_model_definition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ml_model_definition` (
  `model_id` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '模型ID',
  `model_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '模型名称',
  `model_type` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '模型类型(random_forest/xgboost/lightgbm)',
  `factor_list` json NOT NULL COMMENT '使用的因子列表',
  `target_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '预测目标(return_1d/return_5d/return_20d)',
  `model_params` json DEFAULT NULL COMMENT '模型参数',
  `training_config` json DEFAULT NULL COMMENT '训练配置',
  `is_active` tinyint(1) DEFAULT NULL COMMENT '是否启用',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `feature_importance` json DEFAULT NULL COMMENT '特征重要性(训练时保存)',
  PRIMARY KEY (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ml_model_definition`
--

LOCK TABLES `ml_model_definition` WRITE;
/*!40000 ALTER TABLE `ml_model_definition` DISABLE KEYS */;
INSERT INTO `ml_model_definition` VALUES ('1','1','xgboost','[\"momentum_1d\", \"momentum_5d\", \"momentum_20d\", \"volatility_20d\"]','return_5d','{\"n_jobs\": -1, \"max_depth\": 6, \"subsample\": 0.8, \"n_estimators\": 100, \"random_state\": 42, \"learning_rate\": 0.1, \"colsample_bytree\": 0.8}','{\"cv_folds\": 5, \"test_size\": 0.2, \"scaling_method\": \"robust\", \"feature_selection\": true, \"validation_method\": \"time_series_split\", \"feature_selection_k\": 20}',1,'2026-03-19 04:12:09','2026-03-19 04:12:09',NULL),('2','2','xgboost','[\"momentum_1d\", \"momentum_5d\", \"momentum_20d\", \"volatility_20d\"]','return_5d','{\"n_jobs\": -1, \"max_depth\": 6, \"subsample\": 0.8, \"n_estimators\": 100, \"random_state\": 42, \"learning_rate\": 0.1, \"colsample_bytree\": 0.8}','{\"cv_folds\": 5, \"test_size\": 0.2, \"scaling_method\": \"robust\", \"feature_selection\": true, \"validation_method\": \"time_series_split\", \"feature_selection_k\": 20}',1,'2026-03-19 08:29:13','2026-03-19 08:29:13',NULL),('3','3','xgboost','[\"momentum_1d\", \"momentum_5d\", \"momentum_20d\", \"volatility_20d\"]','return_5d','{\"n_jobs\": -1, \"max_depth\": 6, \"subsample\": 0.8, \"n_estimators\": 100, \"random_state\": 42, \"learning_rate\": 0.1, \"colsample_bytree\": 0.8}','{\"cv_folds\": 5, \"test_size\": 0.2, \"scaling_method\": \"robust\", \"feature_selection\": true, \"validation_method\": \"time_series_split\", \"feature_selection_k\": 20}',1,'2026-03-19 09:13:33','2026-03-19 09:13:33',NULL),('5','5','lightgbm','[\"momentum_1d\", \"momentum_5d\", \"momentum_20d\", \"volatility_20d\", \"volume_ratio_20d\"]','return_5d','{\"n_jobs\": -1, \"verbose\": -1, \"max_depth\": 6, \"subsample\": 0.8, \"n_estimators\": 100, \"random_state\": 42, \"learning_rate\": 0.1, \"colsample_bytree\": 0.8}','{\"cv_folds\": 5, \"test_size\": 0.2, \"scaling_method\": \"robust\", \"feature_selection\": true, \"validation_method\": \"time_series_split\", \"feature_selection_k\": 20}',1,'2026-03-21 05:33:50','2026-03-21 05:33:50',NULL),('6','6','random_forest','[\"volatility_20d\", \"volume_ratio_20d\", \"momentum_1d\", \"momentum_5d\", \"momentum_20d\"]','return_20d','{\"n_jobs\": -1, \"max_depth\": 10, \"n_estimators\": 100, \"random_state\": 42, \"min_samples_leaf\": 2, \"min_samples_split\": 5}','{\"cv_folds\": 5, \"test_size\": 0.2, \"scaling_method\": \"robust\", \"feature_selection\": true, \"validation_method\": \"time_series_split\", \"feature_selection_k\": 20}',1,'2026-03-21 11:44:38','2026-03-21 11:44:38',NULL),('7','7','random_forest','[\"momentum_1d\", \"momentum_5d\", \"momentum_20d\", \"volatility_20d\"]','return_20d','{\"n_jobs\": -1, \"max_depth\": 10, \"n_estimators\": 100, \"random_state\": 42, \"min_samples_leaf\": 2, \"min_samples_split\": 5}','{\"cv_folds\": 5, \"test_size\": 0.2, \"scaling_method\": \"robust\", \"feature_selection\": true, \"validation_method\": \"time_series_split\", \"feature_selection_k\": 20}',1,'2026-03-21 13:06:28','2026-03-21 13:06:28',NULL),('764','4654','neural_network','[\"momentum_20d\", \"volatility_20d\"]','return_20d','{}','{\"cv_folds\": 5, \"test_size\": 0.2, \"scaling_method\": \"robust\", \"feature_selection\": true, \"validation_method\": \"time_series_split\", \"feature_selection_k\": 20}',1,'2026-05-06 06:04:23','2026-05-06 06:04:23',NULL),('8','8','random_forest','[\"momentum_1d\", \"momentum_5d\", \"momentum_20d\"]','return_5d','{\"n_jobs\": -1, \"max_depth\": 10, \"n_estimators\": 100, \"random_state\": 42, \"min_samples_leaf\": 2, \"min_samples_split\": 5}','{\"cv_folds\": 5, \"test_size\": 0.2, \"scaling_method\": \"robust\", \"feature_selection\": true, \"validation_method\": \"time_series_split\", \"feature_selection_k\": 20}',1,'2026-04-21 04:24:28','2026-04-21 04:24:28',NULL),('9','9','random_forest','[\"momentum_1d\", \"momentum_5d\", \"momentum_20d\"]','return_5d','{\"n_jobs\": -1, \"max_depth\": 10, \"n_estimators\": 100, \"random_state\": 42, \"min_samples_leaf\": 2, \"min_samples_split\": 5}','{\"cv_folds\": 5, \"test_size\": 0.2, \"scaling_method\": \"robust\", \"feature_selection\": true, \"validation_method\": \"time_series_split\", \"feature_selection_k\": 20}',1,'2026-04-24 10:02:33','2026-04-24 10:02:33',NULL);
/*!40000 ALTER TABLE `ml_model_definition` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-17 17:07:01
