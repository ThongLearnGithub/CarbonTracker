class ApiWalletHistoryItem {
  final String kind;
  final String date;
  final String title;
  final int amount;

  ApiWalletHistoryItem({
    required this.kind,
    required this.date,
    required this.title,
    required this.amount,
  });

  factory ApiWalletHistoryItem.fromJson(Map<String, dynamic> json) {
    return ApiWalletHistoryItem(
      kind: json['kind'] as String,
      date: json['date'] as String,
      title: json['title'] as String,
      amount: json['amount'] as int,
    );
  }
}

class ApiWalletSummary {
  final int userId;
  final int balanceCredits;
  final int creditsThisWeek;
  final int creditsThisMonth;
  final List<ApiWalletHistoryItem> history;

  ApiWalletSummary({
    required this.userId,
    required this.balanceCredits,
    required this.creditsThisWeek,
    required this.creditsThisMonth,
    required this.history,
  });

  factory ApiWalletSummary.fromJson(Map<String, dynamic> json) {
    return ApiWalletSummary(
      userId: json['user_id'] as int,
      balanceCredits: json['balance_credits'] as int,
      creditsThisWeek: json['credits_this_week'] as int,
      creditsThisMonth: json['credits_this_month'] as int,
      history: (json['history'] as List<dynamic>)
          .map((e) => ApiWalletHistoryItem.fromJson(
          e as Map<String, dynamic>))
          .toList(),
    );
  }
}
