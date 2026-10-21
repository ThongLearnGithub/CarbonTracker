import 'dart:convert';

import 'package:http/http.dart' as http;

import 'base_url.dart'
    if (dart.library.io) 'base_url_io.dart'
    if (dart.library.html) 'base_url_web.dart';

import '../models/api_homepage.dart';
import '../models/api_trip.dart';
import '../models/api_trip_stats.dart';
import '../models/api_user.dart';
import '../models/api_voucher.dart';
import '../models/api_wallet.dart';

class ApiService {
  static final String _baseUrl = getBaseUrl();

  Future<LoginResult> login(String email, String password) async {
    final url = Uri.parse('$_baseUrl/auth/login');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return LoginResult.fromJson(data);
    } else {
      throw Exception(response.body);
    }
  }

  Future<LoginResult> loginWithFirebase(String idToken) async {
    final url = Uri.parse('$_baseUrl/auth/firebase');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'id_token': idToken}),
    );

    if (response.statusCode == 200) {
      return LoginResult.fromJson(jsonDecode(response.body));
    }
    throw Exception('Firebase account sync failed: ${response.body}');
  }

  Future<void> signup({
    required String name,
    required String email,
    required String password,
  }) async {
    final url = Uri.parse('$_baseUrl/auth/signup');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'full_name': name,
        'email': email,
        'password': password,
      }),
    );

    if (response.statusCode != 200 && response.statusCode != 201) {
      throw Exception('Failed to sign up: ${response.body}');
    }
  }

  Future<HomePageSummary> fetchHomePageSummary(int userId) async {
    final url = Uri.parse('$_baseUrl/homepage/summary?user_id=$userId');
    final response = await http.get(url);

    if (response.statusCode == 200) {
      return HomePageSummary.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to load homepage summary');
    }
  }

  Future<List<ApiVoucher>> fetchVouchers() async {
    final url = Uri.parse('$_baseUrl/vouchers');
    final response = await http.get(url);

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((e) => ApiVoucher.fromJson(e)).toList();
    } else {
      throw Exception('Failed to load vouchers: ${response.statusCode}');
    }
  }

  Future<ApiVoucher> redeemVoucher(int voucherId, int userId) async {
    final url = Uri.parse('$_baseUrl/vouchers/$voucherId/redeem');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'user_id': userId}),
    );

    if (response.statusCode == 200) {
      return ApiVoucher.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to redeem voucher: ${response.statusCode}');
    }
  }

  Future<ApiTrip> createTrip({
    required int userId,
    required double distanceKm,
    required List<String> transportModes,
    required int credits,
  }) async {
    final today = DateTime.now();
    final formattedDate =
        '${today.year.toString().padLeft(4, '0')}-${today.month.toString().padLeft(2, '0')}-${today.day.toString().padLeft(2, '0')}';

    final url = Uri.parse('$_baseUrl/trips');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'user_id': userId,
        'date': formattedDate,
        'distance_km': distanceKm,
        'transport_modes': transportModes,
        'credits': credits,
      }),
    );

    if (response.statusCode == 200 || response.statusCode == 201) {
      return ApiTrip.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to create trip: ${response.body}');
    }
  }

  Future<List<ApiTrip>> fetchTrips(int userId) async {
    final url = Uri.parse('$_baseUrl/trips?user_id=$userId');
    final response = await http.get(url);

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((e) => ApiTrip.fromJson(e)).toList();
    } else {
      throw Exception('Failed to fetch trips');
    }
  }

  Future<TripStats> fetchTripStats(int userId) async {
    final url = Uri.parse('$_baseUrl/trips/stats?user_id=$userId');
    final response = await http.get(url);

    if (response.statusCode == 200) {
      return TripStats.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to load trip stats');
    }
  }

  Future<ApiWalletSummary> fetchWalletSummary(int userId) async {
    final url = Uri.parse('$_baseUrl/wallet/summary?user_id=$userId');
    final response = await http.get(url);

    if (response.statusCode != 200) {
      throw Exception('Failed to load wallet summary: ${response.body}');
    }

    final Map<String, dynamic> data = jsonDecode(response.body);
    return ApiWalletSummary.fromJson(data);
  }
}
