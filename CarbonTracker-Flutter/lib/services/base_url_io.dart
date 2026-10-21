import 'dart:io';

const _configuredApiBaseUrl = String.fromEnvironment('API_BASE_URL');

String getBaseUrl() {
  if (_configuredApiBaseUrl.isNotEmpty) {
    return _configuredApiBaseUrl.replaceFirst(RegExp(r'/+$'), '');
  }
  if (Platform.isAndroid) {
    return 'http://10.0.2.2:8000';
  }
  return 'http://127.0.0.1:8000';
}
