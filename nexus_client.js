#!/usr/bin/env node

/**
 * Nexus Integration gRPC Client (Node.js)
 * Клиент для подключения PROFI-A backend к Nexus Driver v3.0.0
 */

const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');

const PROTO_PATH = path.join(__dirname, 'nexus_integration.proto');
const SERVER_HOST = process.env.NEXUS_HOST || 'localhost';
const SERVER_PORT = process.env.NEXUS_PORT || 50051;

/**
 * Загрузить proto определения
 */
function loadProto() {
  const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });
  
  return grpc.loadPackageDefinition(packageDefinition);
}

/**
 * NexusSearchClient - клиент для взаимодействия с Nexus gRPC сервером
 */
class NexusSearchClient {
  constructor(host = SERVER_HOST, port = SERVER_PORT) {
    this.host = host;
    this.port = port;
    this.address = `${host}:${port}`;
    this.client = null;
    this.connected = false;
  }

  /**
   * Инициализировать клиент
   */
  connect() {
    try {
      const proto = loadProto();
      const credentials = grpc.credentials.createInsecure();
      
      this.client = new proto.nexus.integration.NexusSearch(
        this.address,
        credentials
      );
      
      this.connected = true;
      console.log(`✅ Connected to Nexus gRPC server at ${this.address}`);
    } catch (error) {
      console.error(`❌ Failed to connect to Nexus: ${error.message}`);
      throw error;
    }
  }

  /**
   * Отключиться от сервера
   */
  disconnect() {
    if (this.client) {
      grpc.closeClient(this.client);
      this.connected = false;
      console.log('Disconnected from Nexus gRPC server');
    }
  }

  /**
   * Быстрый поиск по индексированным проектам и документам
   * 
   * @param {string} query - Поисковый запрос
   * @param {Object} options - Опции поиска
   * @param {number} options.limit - Максимум результатов (по умолчанию 50)
   * @param {string} options.searchType - Тип поиска: "fts5", "semantic", "graph"
   * @param {Object} options.filters - Дополнительные фильтры
   * @returns {Promise<Object>} Результаты поиска
   */
  async search(query, options = {}) {
    if (!this.connected) {
      throw new Error('Not connected to Nexus server');
    }

    return new Promise((resolve, reject) => {
      const request = {
        query: query,
        limit: options.limit || 50,
        search_type: options.searchType || 'fts5',
        filters: options.filters || {},
      };

      this.client.search(request, (error, response) => {
        if (error) {
          reject(new Error(`Search failed: ${error.message}`));
        } else {
          resolve({
            resultCount: response.result_count,
            results: response.results.map(r => ({
              entryId: r.entry_id,
              title: r.title,
              content: r.content,
              relevance: r.relevance,
              entryType: r.entry_type,
              metadata: r.metadata,
              updatedAt: r.updated_at,
            })),
            elapsedMs: response.elapsed_ms,
            error: response.error,
          });
        }
      });
    });
  }

  /**
   * Индексирование документа или файла
   * 
   * @param {string} filePath - Путь до файла
   * @param {Object} options - Опции индексирования
   * @param {string} options.content - Альтернативно, прямое содержимое
   * @param {string} options.contentType - Тип контента
   * @param {Object} options.metadata - Метаданные документа
   * @returns {Promise<Object>} Результат индексирования
   */
  async ingest(filePath, options = {}) {
    if (!this.connected) {
      throw new Error('Not connected to Nexus server');
    }

    return new Promise((resolve, reject) => {
      const request = {
        file_path: filePath,
        content: options.content || '',
        content_type: options.contentType || 'text',
        metadata: options.metadata || {},
      };

      this.client.ingest(request, (error, response) => {
        if (error) {
          reject(new Error(`Ingest failed: ${error.message}`));
        } else {
          resolve({
            entryId: response.entry_id,
            success: response.success,
            message: response.message,
            elapsedMs: response.elapsed_ms,
          });
        }
      });
    });
  }

  /**
   * Сканирование проекта и индексирование всех файлов
   * 
   * @param {string} projectRoot - Корневая папка проекта
   * @param {Object} options - Опции сканирования
   * @param {string[]} options.includePatterns - Включить (*.md, *.py и т.д.)
   * @param {string[]} options.excludePatterns - Исключить (.git, node_modules и т.д.)
   * @param {boolean} options.deepScan - Глубокое сканирование
   * @returns {Promise<Object>} Результаты сканирования
   */
  async scanProject(projectRoot, options = {}) {
    if (!this.connected) {
      throw new Error('Not connected to Nexus server');
    }

    return new Promise((resolve, reject) => {
      const request = {
        project_root: projectRoot,
        include_patterns: options.includePatterns || [],
        exclude_patterns: options.excludePatterns || [],
        deep_scan: options.deepScan || false,
      };

      this.client.scanProject(request, (error, response) => {
        if (error) {
          reject(new Error(`ScanProject failed: ${error.message}`));
        } else {
          resolve({
            filesFound: response.files_found,
            filesIndexed: response.files_indexed,
            files: response.files.map(f => ({
              filePath: f.file_path,
              fileType: f.file_type,
              fileSize: f.file_size,
              language: f.language,
            })),
            success: response.success,
            elapsedMs: response.elapsed_ms,
            error: response.error,
          });
        }
      });
    });
  }

  /**
   * Проверка здоровья системы
   * 
   * @returns {Promise<Object>} Статус системы
   */
  async healthCheck() {
    if (!this.connected) {
      throw new Error('Not connected to Nexus server');
    }

    return new Promise((resolve, reject) => {
      this.client.healthCheck({}, (error, response) => {
        if (error) {
          reject(new Error(`HealthCheck failed: ${error.message}`));
        } else {
          resolve({
            status: response.status,
            version: response.version,
            modules: response.modules,
            stats: response.stats,
          });
        }
      });
    });
  }

  /**
   * Применить конфигурацию (отключение auto-update и т.д.)
   * 
   * @param {Object} config - Конфигурация
   * @param {string} config.mode - "integration"
   * @param {boolean} config.enableAutoUpdate - false для интеграции
   * @param {number} config.updateCheckDays - Игнорируется если enableAutoUpdate=false
   * @param {boolean} config.enableEvents - true по умолчанию
   * @param {boolean} config.enableCaching - true по умолчанию
   * @returns {Promise<Object>} Применённая конфигурация
   */
  async applyConfig(config) {
    if (!this.connected) {
      throw new Error('Not connected to Nexus server');
    }

    return new Promise((resolve, reject) => {
      const request = {
        config: {
          mode: config.mode || 'integration',
          enable_auto_update: config.enableAutoUpdate || false,
          update_check_days: config.updateCheckDays || 15,
          enable_events: config.enableEvents !== false,
          enable_caching: config.enableCaching !== false,
        },
      };

      this.client.applyConfig(request, (error, response) => {
        if (error) {
          reject(new Error(`ApplyConfig failed: ${error.message}`));
        } else {
          resolve({
            success: response.success,
            appliedConfig: response.applied_config,
            message: response.message,
          });
        }
      });
    });
  }

  /**
   * Graceful shutdown
   * 
   * @param {boolean} graceful - Graceful shutdown (по умолчанию true)
   * @returns {Promise<Object>} Результат shutdown
   */
  async shutdown(graceful = true) {
    if (!this.connected) {
      throw new Error('Not connected to Nexus server');
    }

    return new Promise((resolve, reject) => {
      this.client.shutdown({ graceful: graceful }, (error, response) => {
        if (error) {
          reject(new Error(`Shutdown failed: ${error.message}`));
        } else {
          resolve({
            success: response.success,
            message: response.message,
          });
        }
        this.disconnect();
      });
    });
  }
}

// ========== Экспортировать для использования в других модулях ==========

module.exports = NexusSearchClient;

// ========== CLI Demo (если запущен как скрипт) ==========

if (require.main === module) {
  (async () => {
    const client = new NexusSearchClient();
    
    try {
      client.connect();
      
      // Пример: HealthCheck
      console.log('\n📊 Checking Nexus health...');
      const health = await client.healthCheck();
      console.log('Health status:', health.status);
      console.log('Version:', health.version);
      console.log('Modules:', health.modules);
      
      // Пример: Search
      console.log('\n🔍 Searching for "authentication"...');
      const searchResult = await client.search('authentication', {
        limit: 10,
        searchType: 'fts5',
      });
      console.log(`Found ${searchResult.resultCount} results in ${searchResult.elapsedMs.toFixed(2)}ms`);
      if (searchResult.results.length > 0) {
        console.log('Top result:', {
          title: searchResult.results[0].title,
          relevance: searchResult.results[0].relevance,
        });
      }
      
      // Пример: ApplyConfig (убедиться, что auto-update отключен)
      console.log('\n⚙️  Applying integration configuration...');
      const config = await client.applyConfig({
        mode: 'integration',
        enableAutoUpdate: false,
      });
      console.log('Config applied:', config.success);
      
      client.disconnect();
      console.log('\n✅ Demo completed');
      
    } catch (error) {
      console.error('❌ Error:', error.message);
      process.exit(1);
    }
  })();
}
