from django.urls import path
from Media_App import views

urlpatterns = [
    path('', views.index, name='index'),
    path('queryResult.html', views.queryResult, name="queryResult"),
    path('recordsManagement.html', views.recordsManagement, name="recordsManagement"),
    path('rankings.html', views.rankings, name="rankings")
]
