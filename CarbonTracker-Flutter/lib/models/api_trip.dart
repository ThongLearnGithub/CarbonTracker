class ApiTrip {
  final int id;
  final int userId;
  final String date;
  final double distanceKm;
  final List<String> transportModes;
  final int credits;

  ApiTrip({
    required this.id,
    required this.userId,
    required this.date,
    required this.distanceKm,
    required this.transportModes,
    required this.credits,
  });

  factory ApiTrip.fromJson(Map<String, dynamic> json) {
    return ApiTrip(
      id: json['id'],
      userId: json['user_id'],
      date: json['date'],
      distanceKm: (json['distance_km'] as num).toDouble(),
      transportModes: List<String>.from(json['transport_modes']),
      credits: json['credits'],
    );
  }
}
