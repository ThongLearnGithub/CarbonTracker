String getBaseUrl() {
  const configuredUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000',
  );
  return configuredUrl.replaceFirst(RegExp(r'/+$'), '');
}
