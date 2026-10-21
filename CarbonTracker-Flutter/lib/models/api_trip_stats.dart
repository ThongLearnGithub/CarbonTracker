class SeriesPoint {
  final String label;
  final int credits;
  final int trips;

  SeriesPoint({
    required this.label,
    required this.credits,
    required this.trips,
  });

  factory SeriesPoint.fromJson(Map<String, dynamic> json) {
    return SeriesPoint(
      label: json['label'] as String,
      credits: json['credits'] as int,
      trips: json['trips'] as int,
    );
  }
}

class TripStats {
  final int userId;
  final int totalTrips;
  final int totalCredits;
  final List<SeriesPoint> daily;
  final List<SeriesPoint> weekly;
  final List<SeriesPoint> monthly;

  TripStats({
    required this.userId,
    required this.totalTrips,
    required this.totalCredits,
    required this.daily,
    required this.weekly,
    required this.monthly,
  });

  factory TripStats.fromJson(Map<String, dynamic> json) {
    return TripStats(
      userId: json['user_id'] as int,
      totalTrips: json['total_trips'] as int,
      totalCredits: json['total_credits'] as int,
      daily: (json['daily'] as List)
          .map((e) => SeriesPoint.fromJson(e as Map<String, dynamic>))
          .toList(),
      weekly: (json['weekly'] as List)
          .map((e) => SeriesPoint.fromJson(e as Map<String, dynamic>))
          .toList(),
      monthly: (json['monthly'] as List)
          .map((e) => SeriesPoint.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
