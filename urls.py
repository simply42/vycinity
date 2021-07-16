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
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.permissions import IsAuthenticated

from .views import basic_views, customer_views, network_views, firewall_views, change_views

urlpatterns = [
    path('routers/vyos13', basic_views.Vyos13RouterList.as_view()),
    path('routers/vyos13/<uuid:id>', basic_views.Vyos13RouterDetailView.as_view()),
    path('scs/vyos13', basic_views.Vyos13StaticConfigSectionList.as_view()),
    path('scs/vyos13/<uuid:id>', basic_views.Vyos13StaticConfigSectionDetail.as_view()),
    path('configurations/vyos13', basic_views.Vyos13RouterConfigList.as_view()),
    path('deployments', basic_views.DeploymentList.as_view()),
    path('customers', customer_views.CustomerList.as_view()),
    path('customers/<uuid:id>', customer_views.CustomerDetailView.as_view()),
    path('networks', network_views.NetworkList.as_view()),
    path('networks/<uuid:id>', network_views.NetworkDetailView.as_view()),
    path('managedinterfaces', network_views.ManagedInterfaceList.as_view()),
    path('managedinterfaces/<uuid:id>', network_views.ManagedInterfaceDetailView.as_view()),
    path('managedinterfaces/vrrp', network_views.ManagedVRRPInterfaceList.as_view()),
    path('managedinterfaces/vrrp/<uuid:id>', network_views.ManagedVRRPInterfaceDetailView.as_view()),
    path('firewalls', firewall_views.FirewallList.as_view()),
    path('firewalls/<uuid:id>', firewall_views.FirewallDetailView.as_view()),
    path('rulesets', firewall_views.RuleSetList.as_view()),
    path('rulesets/<uuid:id>', firewall_views.RuleSetDetailView.as_view()),
    path('rules/basic', firewall_views.BasicRuleList.as_view()),
    path('rules/basic/<uuid:id>', firewall_views.BasicRuleDetail.as_view()),
    path('rules/custom', firewall_views.CustomRuleList.as_view()),
    path('rules/custom/<uuid:id>', firewall_views.CustomRuleDetail.as_view()),
    path('objects/addresses/networks', firewall_views.NetworkAddressObjectList.as_view()),
    path('objects/addresses/networks/<uuid:id>', firewall_views.NetworkAddressObjectDetail.as_view()),
    path('objects/addresses/lists', firewall_views.ListAddressObjectList.as_view()),
    path('objects/addresses/lists/<uuid:id>', firewall_views.ListAddressObjectDetail.as_view()),
    path('objects/addresses/cidrs', firewall_views.CIDRAddressObjectList.as_view()),
    path('objects/addresses/cidrs/<uuid:id>', firewall_views.CIDRAddressObjectDetail.as_view()),
    path('objects/addresses/hosts', firewall_views.HostAddressObjectList.as_view()),
    path('objects/addresses/hosts/<uuid:id>', firewall_views.HostAddressObjectDetail.as_view()),
    path('objects/services/simple', firewall_views.SimpleServiceObjectList.as_view()),
    path('objects/services/simple/<uuid:id>', firewall_views.SimpleServiceObjectDetail.as_view()),
    path('objects/services/lists', firewall_views.ListServiceObjectList.as_view()),
    path('objects/services/lists/<uuid:id>', firewall_views.ListServiceObjectDetail.as_view()),
    path('objects/services/range', firewall_views.RangeServiceObjectList.as_view()),
    path('objects/services/range/<uuid:id>', firewall_views.RangeServiceObjectDetail.as_view()),
    path('changesets', change_views.ChangeSetList.as_view()),
    path('changesets/<uuid:id>', change_views.ChangeSetDetailView.as_view()),
    path('changes', change_views.ChangeList.as_view()),
    path('changes/<uuid:id>', change_views.ChangeDetailView.as_view()),
    path('schema', get_schema_view(permission_classes=[IsAuthenticated])),
    path('dev-auth/', include('rest_framework.urls'))
]

urlpatterns = format_suffix_patterns(urlpatterns)
