# import Flask class from the flask module
from flask import Flask, request, jsonify, render_template, send_from_directory
import joblib
import os
import numpy as np
import pandas as pd
import regex as re
import string
from sklearn.metrics.pairwise import pairwise_distances
from scipy import spatial
from xgboost import XGBClassifier


app = Flask(__name__)

sentiment_model = XGBClassifier()
sentiment_model.load_model('xgb_sentiment_model.pkl')
print('Log: Loaded sentiment model')
tfidf_vectorizer     = joblib.load('tfidf_vectorizer.pkl')
print('Log: Loaded tfidf vectorizer model')
items_pred = []
processed_data = joblib.load('processed_data.pkl')
print('Log: Loaded data')
data = pd.DataFrame()

print('Log: Building recommendation model')
ratings = processed_data[['items','users','ratings']]
ratings = ratings[~ratings.users.isna()]
ratings = ratings.groupby(by = ['items','users']).mean()
ratings.reset_index(inplace = True)
df_pivot = ratings.pivot(index= 'users'
                        ,columns='items'
                        ,values='ratings'
                        ).T
print('Log: Building pivot model')                        
dummy_train = ratings.copy()                            
dummy_train = dummy_train.pivot(index='users'
                                ,columns='items'
                                ,values='ratings'
                                ).fillna(1)
mean = np.nanmean(df_pivot, axis=1)
df_subtracted = (df_pivot.T-mean).T.fillna(0)
item_correlation = 1 - pairwise_distances(df_subtracted, metric='cosine')
item_correlation[np.isnan(item_correlation)] = 0
item_correlation[item_correlation<0]=0
print(item_correlation)
print('Log: Built similarity matrix') 
item_predicted_ratings = np.dot((df_pivot.fillna(0).T),item_correlation)
item_final_rating = np.multiply(item_predicted_ratings,dummy_train)
print('built item_final_rating')
print('Log: Built recommendation model') 

print('Log: Building sentiment model') 
def vectorizer(i):
    print(i)
    # print(processed_data[processed_data['items']==i])
    reviews_df = pd.DataFrame(processed_data[processed_data['items']==i])
    reviews =  [review for review in reviews_df.reviews]
    v = tfidf_vectorizer.transform(reviews)
    reviews_df = pd.DataFrame(v.toarray(), columns = tfidf_vectorizer.get_feature_names())
    del(v)
    return reviews_df

def get_top_items_from_sentiment_analysis(top_20):
    top_5 = pd.DataFrame(columns=['item','score'])
    for i in top_20:
        item = vectorizer(i)
        score_array = sentiment_model.predict(item)
        score = sum(score_array)/len(score_array)
        print(i,score,len(score_array))
        top_5.loc[len(top_5)] = [i,score]
        del(item,score,score_array)
    top_5 = top_5.sort_values(by='score',ascending=False)[0:5]
    return top_5['item'].values

@app.route('/predict', methods=['POST'])
def predict():
    user = request.form['user']
    user = user.lower()
    if not user or user not in list(ratings.users):
        return render_template('index.html', items_pred = [],showPred= 'N', showError = 'Y')
    top_20 = item_final_rating.loc[user].sort_values(ascending=False)[0:20].index.values
    print(top_20)
    top5 = list(get_top_items_from_sentiment_analysis(top_20))
    
    return render_template('index.html', items_pred = top5,showPred= 'Y', showError = 'N', user = user.title())


@app.route('/', methods=['POST','GET'])
def index():
    if request.method == 'POST':
        return predict()
    else:
        return render_template('index.html',items_pred = [],stars=[],showPred='N', showError='N')

@app.route('/favicon.ico', methods=['GET'])
def index2():
    return jsonify("<p>Hello World!</p>")


if __name__ == '__main__':
    app.debug = False
    app.run(use_reloader=False)

@app.route("/static/<path:path>", methods=['GET'])
def static_dir(path):
    return send_from_directory("static", path)