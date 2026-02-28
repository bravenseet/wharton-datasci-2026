setwd("/Users/zeqinkhoo/Desktop/wharton") 

data = read.csv("cleaned_games.csv")
result = read.csv("result.csv") 
matchup = read.csv("WHSDSC_Rnd1_matchups.csv")
temp_dir <- tempdir() 


power_ranking <- data.frame(
  Team = c("brazil", "netherlands", "peru", "thailand", "pakistan", "india", "china", "panama", "iceland", "philippines", "ethiopia", "singapore",
"guatemala", "uk", "indonesia", "vietnam", "serbia", "uae", "mexico", "new_zealand", "south_korea", "saudi_arabia", "morocco",
"france", "canada", "switzerland", "usa", "germany", "oman", "rwanda", "mongolia", "kazakhstan"), 
  Rating = numeric(32) 
)

for (i in 1:nrow(power_ranking)){
  power_ranking[i, 2] <- 1500 
}


for (m in 1:nrow(data)){
  home <- data[m, 2]
  away <- data[m, 3]
  home_rating <- power_ranking[power_ranking$Team == home,2] 
  away_rating <- power_ranking[power_ranking$Team == away,2]
  
  #probability
  home_expected = 1/(1 + 10^((away_rating - (home_rating + 40))/400))
  away_expected = 1/(1 + 10**(away_rating - (home_rating))/400)
  home_perf = 0.45 * (data[m,"home_goals"] - data[m,"away_goals"]) + 0.45 *(data[m,"home_xg"] - data[m,"away_xg"]) + 0.1 
  home_perf_score = 1/ (1+exp(-2 * home_perf))
  
  away_perf_score = 1 - home_perf_score
  
  power_ranking[power_ranking$Team == home, 2] <- home_rating + 30* (home_perf_score - home_expected) 
  power_ranking[power_ranking$Team == away, 2] <- away_rating + 30* (away_perf_score - away_expected) 
}


sorted_df <- power_ranking %>%
  arrange(desc(Rating))

write.csv(sorted_df, file.path(temp_dir, "Power Ranking.csv"), row.names = FALSE)


train_data <- data.frame(
  game_id = character(1312),
  home_team = character(1312),
  away_team = character(1312), 
  home_rating = numeric(1312),
  away_rating = numeric(1312), 
  rating_diff = numeric(1312),
  home_win = numeric(1312)
)

for (j in 1:1312){
  train_data[j, "game_id"] <- result[j, "game_id"]
  train_data[j, "home_team"] <- result[j, "home_team"]
  train_data[j, "away_team"] <- result[j, "away_team"]
  train_data[j, "home_rating"] <- power_ranking[power_ranking$Team == result[j, "home_team"], 2]
  train_data[j, "away_rating"] <- power_ranking[power_ranking$Team == result[j, "away_team"], 2]
  train_data[j, "rating_diff"] <- train_data[j, "home_rating"] - train_data[j, "away_rating"]
  train_data[j, "home_win"] <- result[j, "home_win"]
}


N = nrow(matchup)
test_data <- data.frame(
  game_id = character(N),
  home_team = character(N),
  away_team = character(N), 
  home_rating = numeric(N),
  away_rating = numeric(N), 
  rating_diff = numeric(N),
  home_win = numeric(N)
)

for (j in 1:N){
  test_data[j, "game_id"] <- matchup[j, "game_id"]
  test_data[j, "home_team"] <- matchup[j, "home_team"]
  test_data[j, "away_team"] <- matchup[j, "away_team"]
  test_data[j, "home_rating"] <- power_ranking[power_ranking$Team == test_data[j, "home_team"], 2]
  test_data[j, "away_rating"] <- power_ranking[power_ranking$Team == test_data[j, "away_team"], 2]
  test_data[j, "rating_diff"] <- test_data[j, "home_rating"] - test_data[j, "away_rating"]
}



model <- glm(home_win ~ rating_diff, data = train_data, family = "binomial")
summary(model)
test_data$home_win = predict(model, newdata = test_data, type="response")
write.csv(test_data, file.path(temp_dir, "Win Probabilities.csv"))
