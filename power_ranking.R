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
  away_expected = 1 - home_expected
  home_perf = 0.45 * (data[m,"home_goals"] - data[m,"away_goals"]) + 0.45 *(data[m,"home_xg"] - data[m,"away_xg"]) + 0.1 
  home_perf_score = 1/ (1+exp(-2 * home_perf))
  
  away_perf_score = 1 - home_perf_score
  
  power_ranking[power_ranking$Team == home, 2] <- home_rating + 30* (home_perf_score - home_expected) 
  power_ranking[power_ranking$Team == away, 2] <- away_rating + 30* (away_perf_score - away_expected) 
}


sorted_df <- power_ranking %>%
  arrange(desc(Rating))

write.csv(sorted_df, file.path(temp_dir, "Power Ranking.csv"), row.names = FALSE)


#part 2: predicting round matchups 
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
train_data$home_win <- as.integer(train_data$home_win == 1)

N = nrow(matchup)
result_data <- data.frame(
  game_id = character(N),
  home_team = character(N),
  away_team = character(N), 
  home_rating = numeric(N),
  away_rating = numeric(N), 
  rating_diff = numeric(N),
  home_win = numeric(N)
)

for (j in 1:N){
  result_data[j, "game_id"] <- matchup[j, "game_id"]
  result_data[j, "home_team"] <- matchup[j, "home_team"]
  result_data[j, "away_team"] <- matchup[j, "away_team"]
  result_data[j, "home_rating"] <- power_ranking[power_ranking$Team == result_data[j, "home_team"], 2]
  result_data[j, "away_rating"] <- power_ranking[power_ranking$Team == result_data[j, "away_team"], 2]
  result_data[j, "rating_diff"] <- result_data[j, "home_rating"] - result_data[j, "away_rating"]
}


#xgboost
x_train <- as.matrix(train_data[1:1000, "rating_diff", drop = FALSE])
y_train <- as.factor(train_data[1:1000, "home_win"])
model_2 <- xgboost(
  data = x_train,
  label = y_train,
  objective = "binary:logistic",
  nrounds = 20,
  verbose = 0
)
result_matrix <- as.matrix(result_data[, "rating_diff", drop = FALSE])

test = as.matrix(train_data[1001:1312, "rating_diff", drop = FALSE]) 
probs <- predict(model_2, newdata = test)
predictions <- cut(probs, 
                 breaks = c(0, 0.5, 1.0), 
                 labels = c(0, 1))
confusionMatrix(predictions, as.factor(train_data[1001:1312, "home_win"]))

result_data$home_win = predict(model_2, newdata = result_matrix)
write.csv(result_data, file.path(temp_dir, "Win Probabilities (XG Boost).csv"))

#logistic regression
model <- glm(home_win ~ rating_diff, data = train_data[1:1000,], family = "binomial")
summary(model)
test_df <- train_data[1001:1312, , drop = FALSE]
prob_2 <- predict(model, newdata = test_df, type="response")
predictions_2 <- cut(prob_2, 
                   breaks = c(-100, 0.5, 100), 
                   labels = c(0, 1))
confusionMatrix(predictions_2, as.factor(train_data[1001:1312, "home_win"]))

result_data$home_win = predict(model, newdata = result_data, type="response")
write.csv(result_data, file.path(temp_dir, "Win Probabilities (Logistic Regression).csv"))

