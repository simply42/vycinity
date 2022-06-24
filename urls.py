# This file is part of VyCinity.
# 
# VyCinity is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
# 
# VyCinity is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with VyCinity. If not, see <https://www.gnu.org/licenses/>.

from django.urls import path, include
from rest_framework.schemas import get_schema_view
#from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.permissions import IsAuthenticated

from vycinity.meta.registries import ChangeableObjectRegistry
from .views import basic_views, customer_views, change_views

urlpatterns = [
    path('routers/vyos13', basic_views.Vyos13RouterList.as_view()),
    path('routers/vyos13/<uuid:id>', basic_views.Vyos13RouterDetailView.as_view()),
    path('scs/vyos13', basic_views.Vyos13StaticConfigSectionList.as_view()),
    path('scs/vyos13/<uuid:id>', basic_views.Vyos13StaticConfigSectionDetail.as_view()),
    path('configurations/vyos13', basic_views.Vyos13RouterConfigList.as_view()),
    path('deployments', basic_views.DeploymentList.as_view()),
    path('customers', customer_views.CustomerList.as_view()),
    path('customers/<uuid:id>', customer_views.CustomerDetailView.as_view()),
    path('changesets', change_views.ChangeSetList.as_view()),
    path('changesets/<uuid:id>', change_views.ChangeSetDetailView.as_view()),
    # Not ready to use yet
    #path('changes', change_views.ChangeList.as_view()),
    #path('changes/<uuid:id>', change_views.ChangeDetailView.as_view()),
    path('schema', get_schema_view(permission_classes=[IsAuthenticated])),
    path('dev-auth/', include('rest_framework.urls'))
]

urlpatterns += ChangeableObjectRegistry.instance().create_url_patterns()

#urlpatterns = format_suffix_patterns(urlpatterns)
