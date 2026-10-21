class DailyCredits {
  final String day;
  final int credits;

  DailyCredits({required this.day, required this.credits});

  factory DailyCredits.fromJson(Map<String, dynamic> json) {
    return DailyCredits(
      day: json['day'],
      credits: json['credits'],
    );
  }
}

class HomePageSummary {
  final int userId;
  final int balanceCredits;
  final int creditsThisWeek;
  final double co2SavedKg;
  final double distanceKm;


  HomePageSummary({
    required this.userId,
    required this.balanceCredits,
    required this.creditsThisWeek,
    required this.co2SavedKg,
    required this.distanceKm,
  });

  factory HomePageSummary.fromJson(Map<String, dynamic> json) {
    return HomePageSummary(
      userId: json['user_id'],
      balanceCredits: json['balance_credits'],
      creditsThisWeek: json['credits_this_week'],
      co2SavedKg: (json['co2_saved_kg'] as num).toDouble(),
      distanceKm: (json['distance_km'] as num).toDouble(),
    );
  }
}
