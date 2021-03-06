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

from django.http import Http404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from vycinity.models.basic_models import Router, Vyos13Router, Vyos13StaticConfigSection, Vyos13RouterConfig, Deployment, DEPLOYMENT_STATE_PREPARATION, DEPLOYMENT_STATE_READY
from vycinity.s42.adapter import vyos13 as Vyos13Adapter
from vycinity.serializers.basic_serializers import Vyos13RouterSerializer, Vyos13StaticConfigSectionSerializer, Vyos13RouterConfigSerializer, DeploymentSerializer
from vycinity.tasks import deploy
from vycinity.views import GenericSchema

class Vyos13RouterList(APIView):
    '''
    Management of VyOS Routers with at least version 1.3.0
    '''
    schema = GenericSchema(serializer=Vyos13RouterSerializer, tags=['router', 'vyos 1.3'], operation_id_base='Vyos13Router', component_name='Vyos13Router')
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        all_routers = Vyos13Router.objects.all()
        return Response(Vyos13RouterSerializer(all_routers, many=True).data)

    def post(self, request, format=None):
        serializer = Vyos13RouterSerializer(data=request.data)
        serializer.data['deploy'] = False
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Vyos13RouterDetailView(APIView):
    '''
    Management of VyOS Routers with at least version 1.3.0
    '''
    schema = GenericSchema(serializer=Vyos13RouterSerializer, tags=['router', 'vyos 1.3'], operation_id_base='Vyos13Router', component_name='Vyos13Router')
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, format=None):
        try:
            result = Vyos13Router.objects.get(pk=id)
            serializer = Vyos13RouterSerializer(result)
            return Response(serializer.data)
        except Vyos13Router.DoesNotExist:
            raise Http404()
    
    def put(self, request, id, format=None):
        try:
            result = Vyos13Router.objects.get(pk=id)
            serializer = Vyos13RouterSerializer(result, data=request.data)
            if serializer.is_valid():
                deploy = False
                if serializer.validated_data['active_static_configs'] != result.active_static_configs:
                    deploy = True
                serializer.save()
                result.refresh_from_db()
                
                if deploy == True and result.deploy:
                    deployment = Deployment(change='changed router', state=DEPLOYMENT_STATE_PREPARATION)
                    deployment.save()
                    generated_config = Vyos13Adapter.generateConfig(result)
                    config = Vyos13RouterConfig(router=result, config=generated_config.config)
                    deployment.configs.add(config)
                    deployment.state = DEPLOYMENT_STATE_READY
                    deployment.save()

                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Vyos13Router.DoesNotExist:
            raise Http404()

    def delete(self, request, id, format=None):
        try:
            result = Vyos13Router.objects.get(pk=id)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Vyos13Router.DoesNotExist:
            raise Http404()

class Vyos13StaticConfigSectionList(APIView):
    '''
    Management of static configuration sections for VyOS 1.3
    '''
    schema = GenericSchema(serializer=Vyos13StaticConfigSectionSerializer, tags=['static config section', 'vyos 1.3'], operation_id_base='Vyos13StaticConfigSection', component_name='Vyos13StaticConfigSection')
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        all_static_configs = Vyos13StaticConfigSection.objects.all()
        return Response(Vyos13StaticConfigSectionSerializer(all_static_configs, many=True).data)

    def post(self, request, format=None):
        serializer = Vyos13StaticConfigSectionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Vyos13StaticConfigSectionDetail(APIView):
    '''
    Management of static configuration sections for VyOS 1.3
    '''
    schema = GenericSchema(serializer=Vyos13StaticConfigSectionSerializer, tags=['static config section', 'vyos 1.3'], operation_id_base='Vyos13StaticConfigSection', component_name='Vyos13StaticConfigSection')
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id, format=None):
        try:
            result = Vyos13StaticConfigSection.objects.get(pk=id)
            serializer = Vyos13StaticConfigSectionSerializer(result)
            return Response(serializer.data)
        except Vyos13StaticConfigSection.DoesNotExist:
            raise Http404()
    
    def put(self, request, id, format=None):
        try:
            result = Vyos13StaticConfigSection.objects.get(pk=id)
            serializer = Vyos13StaticConfigSectionSerializer(result, data=request.data)
            if serializer.is_valid():
                serializer.save()

                routers = Vyos13Router.objects.filter(active_static_configs__in=[result]).distinct()
                deployment = Deployment(state=DEPLOYMENT_STATE_PREPARATION, change='change static_config_section')
                deployment.save()
                for router in routers:
                    generated_config = Vyos13Adapter.generateConfig(router)
                    config = Vyos13RouterConfig(router=router, config=generated_config.config)
                    config.save()
                    deployment.configs.add(config)
                deployment.state = DEPLOYMENT_STATE_READY
                deployment.save()

                deploy.delay(deployment.pk)

                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Vyos13StaticConfigSection.DoesNotExist:
            raise Http404()

    def delete(self, request, id, format=None):
        try:
            result = Vyos13StaticConfigSection.objects.get(pk=id)
            result.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Vyos13StaticConfigSection.DoesNotExist:
            raise Http404()


class DeploymentList(APIView):
    '''
    get:
        Retrieve information about triggered deployments to routers.
    '''
    schema = GenericSchema(serializer=DeploymentSerializer, tags=['deployment'], operation_id_base='Deployment', component_name='Deployment')
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        all_deployments = Deployment.objects.all()
        return Response(DeploymentSerializer(all_deployments, many=True).data)


class Vyos13RouterConfigList(APIView):
    '''
    get:
        The list for configuration for VyOS 1.3 routers
    '''
    schema = GenericSchema(serializer=Vyos13RouterConfigSerializer, tags=['router', 'vyos 1.3', 'configuration'], operation_id_base='Vyos13RouterConfig', component_name='Vyos13RouterConfig')
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        all_configs = Vyos13RouterConfig.objects.all()
        return Response(Vyos13RouterConfigSerializer(all_configs, many=True).data)

