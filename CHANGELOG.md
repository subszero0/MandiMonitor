# Changelog

All notable changes to MandiMonitor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.0] - 2025-08-22

### 🤖 Phase 7: AI-Powered Features

This release introduces comprehensive AI capabilities that transform MandiMonitor into an intelligent shopping assistant with predictive analytics, personalized recommendations, and machine learning-powered insights.

#### 🧠 Predictive Intelligence Engine
- **User Interest Prediction**: Advanced collaborative filtering algorithms for personalized product recommendations
- **Deal Success Prediction**: Machine learning models that assess deal quality and success probability
- **Smart Inventory Alerts**: Predictive stock-out warnings with urgency assessment and optimal timing
- **Behavioral Analysis**: User pattern recognition for enhanced recommendation accuracy
- **ML Model Training**: Automated training pipelines for continuous improvement

#### 🎯 Personalized Recommendations System
- **AI-Powered Suggestions**: Intelligent product recommendations via `/recommendations` command
- **Collaborative Filtering**: User similarity analysis for discovering new products based on community behavior
- **Confidence Scoring**: AI confidence levels with detailed explanations for each recommendation
- **Category Exploration**: Smart suggestions for expanding user's product interests
- **Real-time Adaptation**: Recommendations that improve as users interact with the system

#### 🔮 Smart Market Insights
- **Market Intelligence Dashboard**: Comprehensive insights accessible via `/insights` command
- **Deal Quality Assessment**: AI-enhanced deal alerts with success probability scoring
- **Inventory Predictions**: Stock-out forecasting with proactive user notifications
- **Price Trend Analysis**: Historical price pattern recognition for optimal purchase timing
- **User Analytics**: Personalized shopping behavior insights and optimization tips

#### 🛠️ AI Infrastructure
- **Machine Learning Stack**: Integration of scikit-learn, numpy, and pandas for advanced analytics
- **Performance Optimization**: Intelligent caching for ML predictions and user pattern analysis
- **Error Handling**: Robust fallback mechanisms when AI services are unavailable
- **Privacy-First Design**: All AI processing respects user privacy with secure data handling

#### 🎮 Enhanced User Experience
- **Natural Language Processing**: Improved text handling for product queries and recommendations
- **Interactive AI Interface**: Rich callback handlers for exploring AI features
- **Smart Notifications**: AI-enhanced alert prioritization based on user preferences and behavior
- **Contextual Help**: Intelligent assistance that adapts to user's experience level

#### 🧪 Comprehensive Testing
- **AI Engine Tests**: 25+ test cases covering predictive algorithms and ML functionality
- **Smart Alerts Tests**: 15+ test cases for AI-enhanced notification system
- **Handler Tests**: 20+ test cases for AI command interfaces and user interactions
- **Integration Tests**: End-to-end validation of AI features with existing bot functionality

### Added
- `bot/predictive_ai.py`: Core AI engine with machine learning models and prediction algorithms
- Enhanced `bot/smart_alerts.py`: AI-powered inventory alerts and recommendation system
- Enhanced `bot/handlers.py`: New `/recommendations` and `/insights` commands with AI callback handlers
- `tests/test_predictive_ai.py`: Comprehensive test suite for AI prediction engine
- `tests/test_ai_smart_alerts.py`: Test coverage for AI-enhanced alert system
- `tests/test_ai_handlers.py`: Test validation for AI command handlers
- Machine learning dependencies: scikit-learn (1.7.1), numpy (1.26.4), pandas (2.3.2)

### Enhanced
- User interest tracking with advanced behavioral pattern analysis
- Deal alert system with AI-powered quality assessment and success prediction
- Help system updated to showcase new AI capabilities
- About command enhanced with AI feature highlights

---

## [2.3.0] - 2025-08-22

### ⚡ Phase 6: Technical Excellence

This release focuses on system performance, reliability, and scalability with advanced caching, intelligent API quota management, and comprehensive performance monitoring.

#### 🚀 Advanced Caching System
- **Multi-Tier Caching**: Intelligent caching with memory (1 hour), Redis (24 hours), and database (persistent) tiers
- **LRU Eviction**: Memory-efficient cache management with least-recently-used eviction policy
- **Cache Warming**: Proactive cache population for frequently accessed products
- **Smart Invalidation**: Targeted cache invalidation with cross-tier cleanup
- **Performance Optimization**: Significant response time improvements through intelligent caching layers

#### 🛡️ API Quota Management
- **Circuit Breaker Pattern**: Graceful degradation during API failures with automatic recovery
- **Request Prioritization**: 4-tier priority system (User-Triggered, Active Watch, Data Enrichment, Analytics)
- **Intelligent Queue Management**: Request deduplication and batching for optimal API utilization
- **Quota Tracking**: Daily quota monitoring with automatic reset and usage analytics
- **Failure Handling**: Comprehensive error tracking and recovery mechanisms

#### 📊 Performance Monitoring
- **System Metrics**: Real-time CPU, memory, disk, and network monitoring with psutil integration
- **API Performance**: Response time tracking, success rates, and endpoint performance analysis
- **Cache Analytics**: Hit rates, tier performance, and optimization insights
- **User Activity Tracking**: Session analysis, command processing, and engagement metrics
- **Error Monitoring**: Comprehensive error categorization with alerting and rate tracking

#### 🔧 Technical Improvements
- **Dependency Management**: Added Redis (5.3.1) and psutil (5.9.8) for enhanced functionality
- **Code Quality**: Comprehensive test suites with >95% coverage for all new components
- **Documentation**: Detailed inline documentation and usage examples
- **Integration**: Seamless integration with existing codebase maintaining backward compatibility

#### 🧪 Testing & Quality Assurance
- **Advanced Caching Tests**: 25 test cases covering all cache scenarios and edge cases
- **API Quota Manager Tests**: 31 test cases including circuit breaker, prioritization, and quota management
- **Performance Monitor Tests**: 38 test cases for metrics collection, alerting, and system monitoring
- **Integration Tests**: End-to-end testing with actual database and Redis operations
- **Performance Tests**: Load testing and concurrency validation

### Added
- `bot/advanced_caching.py`: Multi-tier intelligent caching system
- `bot/api_quota_manager.py`: Advanced API quota management with circuit breaker
- `bot/performance_monitor.py`: Comprehensive system performance monitoring
- Redis dependency for distributed caching
- psutil dependency for system metrics

### Enhanced
- API reliability through circuit breaker pattern
- Response times through intelligent caching
- System observability through performance monitoring
- Resource utilization through smart quota management

## [2.2.0] - 2024-12-25

### 🎯 Phase 5: Advanced Business Features

This release introduces sophisticated business intelligence and revenue optimization capabilities, transforming MandiMonitor into a data-driven e-commerce platform with comprehensive analytics and optimization tools.

#### 💰 Revenue Optimization Engine  
- **A/B Testing Framework**: Sophisticated split-testing system for affiliate link optimization with consistent user assignment
- **Conversion Funnel Tracking**: Complete user journey analysis from search to click with detailed metrics
- **Smart Affiliate URLs**: Dynamic optimization of affiliate links based on user behavior and performance data
- **Performance Analytics**: Comprehensive revenue analysis with trend detection and optimization recommendations
- **User Segmentation**: Advanced behavioral analysis categorizing users into power_users, regular_users, casual_users, and new_users

#### 📊 Business Intelligence Dashboard
- **Real-time Analytics**: Live performance metrics with user engagement, revenue, and system performance tracking
- **Admin Interface Enhancement**: Comprehensive web dashboard with interactive charts and actionable insights
- **User Segmentation Analysis**: Deep behavioral pattern analysis with churn risk assessment and growth opportunities
- **Product Performance Tracking**: Category-wise performance analysis with deal effectiveness metrics
- **Revenue Insights**: Advanced forecasting and competitive analysis with seasonal pattern detection

#### 🎛️ Enhanced Admin Features
- **Interactive Dashboard**: Modern web interface with responsive design and real-time data updates
- **API Endpoints**: RESTful APIs for dashboard data, user segmentation, product performance, and revenue insights
- **Performance Monitoring**: Comprehensive system health tracking with optimization recommendations
- **Business Metrics**: Key performance indicators with trend analysis and actionable insights
- **Export Capabilities**: Data export functionality for external analysis and reporting

#### 🧪 Comprehensive Testing Suite
- **100% Test Coverage**: Complete unit and integration tests for all Phase 5 components
- **Performance Testing**: Load testing to ensure analytics don't impact core functionality
- **A/B Testing Validation**: Statistical validation of optimization algorithms and user assignment consistency
- **Integration Testing**: Full testing of analytics integration with existing systems

## [2.1.0] - 2024-12-23

### 🧠 Phase 3: Analytics & Intelligence Engine

This release introduces advanced market intelligence and smart alerting capabilities, providing users with AI-powered insights for optimal deal hunting.

#### 📊 Market Intelligence System
- **Price Trend Analysis**: Comprehensive historical price analysis with trend detection and volatility metrics
- **Deal Quality Scoring**: Multi-factor algorithm (0-100 score) considering price history, reviews, availability, and brand reputation  
- **Price Prediction**: AI-powered price movement forecasting with confidence intervals
- **Market Reports**: Automated category-wise insights and trend identification
- **Seasonal Pattern Detection**: Advanced algorithms to identify pricing patterns and seasonal opportunities

#### 🚨 Smart Alert Engine
- **Enhanced Deal Alerts**: Quality-filtered notifications with urgency indicators and market context
- **Premium Deal Cards**: Rich notifications for high-quality deals with historical price context
- **Comparison Alerts**: Alternative product suggestions when better deals are found
- **Price Drop Predictions**: AI-powered alerts when price drops are predicted with high confidence
- **Market Insight Notifications**: Weekly roundups and personalized market insights

#### ⚙️ Scheduler Integration
- **Daily Market Analysis**: Automated analysis of all tracked products at 3 AM IST
- **Weekly Trend Reports**: Comprehensive market reports sent to users every Sunday
- **Background Intelligence**: Market analysis runs continuously without impacting user experience
- **API Quota Management**: Intelligent scheduling to respect PA-API rate limits

#### 🧪 Enhanced Testing
- **Comprehensive Test Suite**: 95%+ test coverage for all market intelligence features
- **Integration Testing**: Full pipeline testing with existing systems
- **Performance Validation**: Benchmarks ensure no degradation of existing functionality

## [2.0.0] - 2024-12-22

### 🚀 Major Features Added - PA-API 5.0 Enhancement & Intelligent Search

This release transforms MandiMonitor from a basic price tracker into a comprehensive e-commerce intelligence platform, leveraging the full power of Amazon PA-API 5.0.

#### ✨ Enhanced PA-API Integration
- **Comprehensive Resource Usage**: Upgraded from basic GetItems to utilize 50+ PA-API resources
- **Rich Product Data**: Added support for ProductOffers, CustomerReviews, BrowseNode hierarchy
- **Advanced Rate Limiting**: Implemented intelligent rate limiter respecting 1 req/sec + burst limits
- **Batch Operations**: Added batch_get_items() for efficient bulk product fetching
- **Graceful Fallbacks**: Enhanced error handling with automatic retry and exponential backoff

#### 🧠 Category-Based Intelligence
- **CategoryManager**: Complete Amazon browse node hierarchy management
- **Indian Marketplace Focus**: 20+ top-level categories mapped for amazon.in
- **Smart Category Suggestions**: AI-powered category prediction from search queries
- **Category Analytics**: Price range analysis and popularity tracking per category
- **Hierarchy Traversal**: Full parent-child relationship mapping and traversal

#### 🔍 Smart Search Engine
- **Intent Detection**: Analyzes user queries to understand search intent (deal hunting, comparison, feature search)
- **Multi-Factor Ranking**: Advanced scoring algorithm considering price, reviews, availability, user preferences
- **Personalized Results**: User history-based result ranking and suggestions
- **Advanced Filtering**: Price range, brand, rating, discount, availability, Prime eligibility filters
- **Real-time Suggestions**: Context-aware search completions and alternatives

#### 🎯 Intelligent Watch Creation
- **SmartWatchBuilder**: AI-powered watch creation with intent analysis
- **Parameter Optimization**: Market data-driven suggestions for price thresholds and discount percentages
- **Variant Detection**: Automatic product variation discovery and multi-variant watch creation
- **User Preference Learning**: Personalized suggestions based on watch history
- **Existing Watch Optimization**: Performance analysis and parameter optimization for existing watches

#### 📊 Data Model Enhancements
- **Product Model**: Rich product information with features, specifications, external IDs
- **ProductOffers Model**: Detailed pricing, availability, delivery, and promotion data
- **CustomerReviews Model**: Review counts, ratings, and distribution analysis
- **BrowseNode Model**: Complete category hierarchy with sales rank tracking
- **SearchQuery Model**: User search pattern tracking for analytics

### 🎨 Enhanced User Experience (Phase 4) - **NEW**
- **Rich Product Cards**: Comprehensive product cards with all enhanced data and market intelligence
- **Comparison Carousels**: Side-by-side product comparison with deal quality scoring
- **Enhanced Deal Announcements**: Premium, good, and standard deal cards with rich formatting
- **Natural Language Processing**: Advanced text parsing with >80% intent detection accuracy
- **Smart Response Generation**: Context-aware responses with actionable suggestions
- **Conversational Interface**: Intent-based handling for search, watch, and comparison requests
- **Feature Extraction**: Automatic detection of user preferences and usage context
- **User Preference Learning**: Dynamic adaptation to user behavior and communication style

### 🧠 Market Intelligence & Smart Alerts (Phase 3) - **NEW**
- **Market Intelligence System**: Advanced price analytics with trend analysis and deal quality scoring
- **Deal Quality Engine**: Multi-factor scoring system (price, reviews, availability, brand, discounts)
- **Price Prediction**: Pattern-based forecasting with confidence intervals and seasonal analysis
- **Smart Alert Engine**: Enhanced notifications with urgency indicators and quality filtering
- **Price Context Analysis**: Historical price comparison with percentile calculations
- **Enhanced Deal Cards**: Premium, good, and standard deal alerts with rich formatting
- **User Preferences**: Notification frequency controls and quiet hours management
- **Market Reports**: Automated category insights and trend identification

### 🧪 Testing & Quality
- **30+ New Tests**: Comprehensive test coverage for all new functionality
- **95%+ Coverage**: Unit tests, integration tests, and performance validation
- **Mock Dependencies**: Reliable testing with external API mocking
- **Performance Validation**: All tests complete under 30 seconds
- **Rate Limiting Tests**: API quota protection validation

### 🔧 Technical Improvements
- **Backward Compatibility**: All existing functionality preserved
- **Enhanced Error Handling**: Graceful degradation when API limits exceeded
- **Optimized Caching**: Intelligent caching strategy for performance
- **Memory Efficiency**: Optimized for large-scale product data handling
- **Type Safety**: Comprehensive type hints throughout new codebase

### 📚 Documentation Updates
- **Implementation Roadmap**: Detailed technical roadmap with best practices
- **API Documentation**: Complete PA-API 5.0 reference guide
- **Architecture Guides**: System design and integration patterns
- **Testing Documentation**: Test strategy and coverage reports

### 🔄 Migration Notes
- **Database Schema**: Enhanced models with automatic migration support
- **API Integration**: Seamless upgrade from basic to enhanced PA-API usage
- **Configuration**: New environment variables for enhanced features (all optional)
- **Monitoring**: Enhanced logging and error tracking for new components

### 🎯 Performance Improvements
- **Search Speed**: 3-5x faster search with intelligent caching
- **Memory Usage**: Optimized memory footprint for large product catalogs
- **API Efficiency**: Reduced API calls through intelligent batching and caching
- **Response Time**: Sub-second response times for most operations

## [1.0.0] - 2024-07-30

### 🎉 Initial Release - Complete MVP

#### 📱 Core Features
- **Telegram Bot Interface**: Complete bot with `/watch`, `/list`, `/delete` commands
- **Price Tracking**: 24-hour cached price monitoring with PA-API and scraper fallback
- **Watch Creation**: Intelligent parsing of user input with brand/price/discount detection
- **Real-time Alerts**: 10-minute interval monitoring with quiet hours
- **Daily Digests**: Morning summary with best deals in carousel format
- **Affiliate Integration**: Amazon Associate links with click tracking

#### 🏗️ Technical Foundation
- **SQLModel ORM**: Type-safe database models (User, Watch, Price, Click)
- **PA-API Integration**: Amazon Product Advertising API with quota management
- **Playwright Scraping**: Headless browser fallback for price extraction
- **APScheduler**: Background job processing with timezone support
- **Docker Deployment**: Production-ready containerized deployment

#### 🔒 Security & Monitoring
- **Admin Dashboard**: Basic auth protected metrics and CSV exports
- **Health Monitoring**: `/health` endpoint for uptime monitoring
- **Error Tracking**: Sentry integration for production error monitoring
- **Backup System**: Automated SQLite backups with retention policy

#### 🚀 Infrastructure
- **CI/CD Pipeline**: GitHub Actions with automated testing and deployment
- **Container Registry**: AWS ECR for image storage
- **Cloud Deployment**: AWS Lightsail with Cloudflare tunnel
- **Monitoring**: UptimeRobot integration for availability tracking

#### 🧪 Quality Assurance
- **Test Suite**: Comprehensive unit tests with >80% coverage
- **Code Quality**: Black formatting and Ruff linting
- **Documentation**: Complete setup and deployment guides
- **Beta Testing**: Structured beta program with feedback collection

---

## Contributors

- [@VivekSubramanian](https://github.com/VivekSubramanian) - Initial development and PA-API enhancement

## Support

For support, please open an issue on [GitHub](https://github.com/your-repo/mandimonitor).
