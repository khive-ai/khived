# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import AsyncMock, patch

import pytest
from khive.clients.executor import AsyncExecutor
from khive.services.info.info_service import InfoServiceGroup
from khive.services.info.parts import InfoAction, InfoResponse, SearchProvider


class TestInfoServiceGroup:
    """Tests for the InfoServiceGroup class."""

    def test_info_service_initialization(self):
        """Test that InfoServiceGroup initializes with None endpoints."""
        # Act
        service = InfoServiceGroup()

        # Assert
        assert service._perplexity is None
        assert service._exa is None
        assert service._openrouter is None
        assert isinstance(service._executor, AsyncExecutor)

    @pytest.mark.asyncio
    async def test_perplexity_search_success(self, mocker):
        """Test that _perplexity_search correctly uses the endpoint."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={"result": "success"})

        # Mock the match_endpoint function
        mocker.patch(
            "khive.services.info.info_service.match_endpoint",
            return_value=mock_endpoint,
        )

        # Mock the PerplexityChatRequest class
        mock_request = mocker.Mock()
        mocker.patch(
            "khive.connections.providers.perplexity_.PerplexityChatRequest",
            return_value=mock_request,
        )

        service = InfoServiceGroup()
        params = {"query": "test"}

        # Act
        response = await service._perplexity_search(params)

        # Assert
        assert response.success is True
        assert response.action_performed == InfoAction.SEARCH
        assert response.content == {"result": "success"}
        mock_endpoint.call.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_perplexity_search_error(self, mocker):
        """Test that _perplexity_search correctly handles errors."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(side_effect=Exception("Test error"))

        # Mock the match_endpoint function
        mocker.patch(
            "khive.services.info.info_service.match_endpoint",
            return_value=mock_endpoint,
        )

        # Mock the PerplexityChatRequest class
        mock_request = mocker.Mock()
        mocker.patch(
            "khive.connections.providers.perplexity_.PerplexityChatRequest",
            return_value=mock_request,
        )

        service = InfoServiceGroup()
        params = {"query": "test"}

        # Act
        response = await service._perplexity_search(params)

        # Assert
        assert response.success is False
        assert response.action_performed == InfoAction.SEARCH
        assert "Perplexity search error: Test error" in response.error
        mock_endpoint.call.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_perplexity_search_endpoint_none(self, mocker):
        """Test that _perplexity_search handles None endpoint."""
        # Arrange
        mocker.patch(
            "khive.services.info.info_service.match_endpoint", return_value=None
        )

        service = InfoServiceGroup()
        params = {"query": "test"}

        # Act
        response = await service._perplexity_search(params)

        # Assert
        assert response.success is False
        assert response.action_performed == InfoAction.SEARCH
        assert "Perplexity search error" in response.error

    @pytest.mark.asyncio
    async def test_exa_search_success(self, mocker):
        """Test that _exa_search correctly uses the endpoint."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={"result": "success"})

        # Mock the match_endpoint function
        mocker.patch(
            "khive.services.info.info_service.match_endpoint",
            return_value=mock_endpoint,
        )

        # Mock the ExaSearchRequest class
        mock_request = mocker.Mock()
        mocker.patch(
            "khive.connections.providers.exa_.ExaSearchRequest",
            return_value=mock_request,
        )

        service = InfoServiceGroup()
        params = {"query": "test"}

        # Act
        response = await service._exa_search(params)

        # Assert
        assert response.success is True
        assert response.action_performed == InfoAction.SEARCH
        assert response.content == {"result": "success"}
        mock_endpoint.call.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_exa_search_error(self, mocker):
        """Test that _exa_search correctly handles errors."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(side_effect=Exception("Test error"))

        # Mock the match_endpoint function
        mocker.patch(
            "khive.services.info.info_service.match_endpoint",
            return_value=mock_endpoint,
        )

        # Mock the ExaSearchRequest class
        mock_request = mocker.Mock()
        mocker.patch(
            "khive.connections.providers.exa_.ExaSearchRequest",
            return_value=mock_request,
        )

        service = InfoServiceGroup()
        params = {"query": "test"}

        # Act
        response = await service._exa_search(params)

        # Assert
        assert response.success is False
        assert response.action_performed == InfoAction.SEARCH
        assert "Exa search error: Test error" in response.error
        mock_endpoint.call.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_exa_search_endpoint_none(self, mocker):
        """Test that _exa_search handles None endpoint."""
        # Arrange
        mocker.patch(
            "khive.services.info.info_service.match_endpoint", return_value=None
        )

        service = InfoServiceGroup()
        params = {"query": "test"}

        # Act
        response = await service._exa_search(params)

        # Assert
        assert response.success is False
        assert response.action_performed == InfoAction.SEARCH
        assert "Exa search error" in response.error

    @pytest.mark.asyncio
    async def test_make_model_call_success(self, mocker):
        """Test that _make_model_call correctly calls the endpoint."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={"result": "success"})

        service = InfoServiceGroup()
        service._openrouter = mock_endpoint
        payload = {"messages": [{"role": "user", "content": "test"}]}

        # Act
        result = await service._make_model_call(payload)

        # Assert
        assert result == {"result": "success"}
        mock_endpoint.call.assert_called_once_with(payload)

    @pytest.mark.asyncio
    async def test_make_model_call_error(self, mocker):
        """Test that _make_model_call correctly handles errors."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(side_effect=Exception("Test error"))

        service = InfoServiceGroup()
        service._openrouter = mock_endpoint
        payload = {"messages": [{"role": "user", "content": "test"}]}

        # Act
        result = await service._make_model_call(payload)

        # Assert
        assert "error" in result
        assert "Test error" in result["error"]
        mock_endpoint.call.assert_called_once_with(payload)

    @pytest.mark.asyncio
    async def test_consult_success(self, mocker):
        """Test that _consult correctly uses the executor."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={"result": "success"})

        # Mock the match_endpoint function
        mocker.patch(
            "khive.services.info.info_service.match_endpoint",
            return_value=mock_endpoint,
        )

        # Mock the executor map method
        mock_map = AsyncMock(
            return_value=[
                ("model1", {"result": "success1"}),
                ("model2", {"result": "success2"}),
            ]
        )
        mock_executor = mocker.Mock()
        mock_executor.map = mock_map

        service = InfoServiceGroup()
        service._executor = mock_executor

        # Create a mock for InfoConsultParams that bypasses validation
        with patch("khive.services.info.parts.InfoConsultParams") as MockParams:
            mock_params = MockParams.return_value
            mock_params.models = ["model1", "model2"]
            mock_params.question = "test question"
            mock_params.system_prompt = "test prompt"

            # Act
            response = await service._consult(mock_params)

        # Assert
        assert response.success is True
        assert response.action_performed == InfoAction.CONSULT
        assert "model1" in response.content
        assert "model2" in response.content
        assert response.content["model1"] == {"result": "success1"}
        assert response.content["model2"] == {"result": "success2"}

    @pytest.mark.asyncio
    async def test_consult_endpoint_none(self, mocker):
        """Test that _consult handles None endpoint."""
        # Arrange
        mocker.patch(
            "khive.services.info.info_service.match_endpoint", return_value=None
        )

        service = InfoServiceGroup()

        # Create a mock for InfoConsultParams that bypasses validation
        with patch("khive.services.info.parts.InfoConsultParams") as MockParams:
            mock_params = MockParams.return_value
            mock_params.models = ["model1"]
            mock_params.question = "test question"
            mock_params.system_prompt = "test prompt"

            # Act
            response = await service._consult(mock_params)

        # Assert
        assert response.success is False
        assert response.action_performed == InfoAction.CONSULT
        assert "Consult error" in response.error

    @pytest.mark.asyncio
    async def test_handle_request_perplexity_search(self, mocker):
        """Test that handle_request correctly routes Perplexity search requests."""
        # Arrange
        mock_perplexity_search = mocker.patch.object(
            InfoServiceGroup,
            "_perplexity_search",
            autospec=True,
            return_value=InfoResponse(
                success=True,
                action_performed=InfoAction.SEARCH,
                content={"result": "success"},
            ),
        )

        service = InfoServiceGroup()

        # Create a mock for InfoRequest that bypasses validation
        with (
            patch("khive.services.info.parts.InfoRequest") as MockRequest,
            patch("khive.services.info.parts.InfoSearchParams") as MockSearchParams,
        ):
            mock_request = MockRequest.return_value
            mock_request.action = InfoAction.SEARCH

            mock_params = MockSearchParams.return_value
            mock_params.provider = SearchProvider.PERPLEXITY
            mock_params.provider_params = {"query": "test"}

            mock_request.params = mock_params

            # Act
            response = await service.handle_request(mock_request)

        # Assert
        assert response.success is True
        assert response.action_performed == InfoAction.SEARCH
        assert response.content == {"result": "success"}
        mock_perplexity_search.assert_called_once_with(service, {"query": "test"})

    @pytest.mark.asyncio
    async def test_handle_request_exa_search(self, mocker):
        """Test that handle_request correctly routes Exa search requests."""
        # Arrange
        mock_exa_search = mocker.patch.object(
            InfoServiceGroup,
            "_exa_search",
            autospec=True,
            return_value=InfoResponse(
                success=True,
                action_performed=InfoAction.SEARCH,
                content={"result": "success"},
            ),
        )

        service = InfoServiceGroup()

        # Create a mock for InfoRequest that bypasses validation
        with (
            patch("khive.services.info.parts.InfoRequest") as MockRequest,
            patch("khive.services.info.parts.InfoSearchParams") as MockSearchParams,
        ):
            mock_request = MockRequest.return_value
            mock_request.action = InfoAction.SEARCH

            mock_params = MockSearchParams.return_value
            mock_params.provider = SearchProvider.EXA
            mock_params.provider_params = {"query": "test"}

            mock_request.params = mock_params

            # Act
            response = await service.handle_request(mock_request)

        # Assert
        assert response.success is True
        assert response.action_performed == InfoAction.SEARCH
        assert response.content == {"result": "success"}
        mock_exa_search.assert_called_once_with(service, {"query": "test"})

    @pytest.mark.asyncio
    async def test_handle_request_consult(self, mocker):
        """Test that handle_request correctly routes consult requests."""
        # Arrange
        mock_consult = mocker.patch.object(
            InfoServiceGroup,
            "_consult",
            autospec=True,
            return_value=InfoResponse(
                success=True,
                action_performed=InfoAction.CONSULT,
                content={"model1": {"result": "success"}},
            ),
        )

        service = InfoServiceGroup()

        # Create a mock for InfoRequest that bypasses validation
        with (
            patch("khive.services.info.parts.InfoRequest") as MockRequest,
            patch("khive.services.info.parts.InfoConsultParams") as MockConsultParams,
        ):
            mock_request = MockRequest.return_value
            mock_request.action = InfoAction.CONSULT

            mock_params = MockConsultParams.return_value
            mock_params.question = "test question"
            mock_params.models = ["model1"]
            mock_params.system_prompt = "test prompt"

            mock_request.params = mock_params

            # Act
            response = await service.handle_request(mock_request)

        # Assert
        assert response.success is True
        assert response.action_performed == InfoAction.CONSULT
        assert response.content == {"model1": {"result": "success"}}
        mock_consult.assert_called_once_with(service, mock_params)

    @pytest.mark.asyncio
    async def test_handle_request_invalid_action(self, mocker):
        """Test that handle_request correctly handles invalid actions."""
        # Arrange
        service = InfoServiceGroup()

        # Create a mock for InfoRequest that bypasses validation
        with patch("khive.services.info.parts.InfoRequest") as MockRequest:
            mock_request = MockRequest.return_value
            mock_request.action = "INVALID_ACTION"

            # Act
            response = await service.handle_request(mock_request)

        # Assert
        assert response.success is False
        assert "Invalid action" in response.error

    @pytest.mark.asyncio
    async def test_close(self, mocker):
        """Test that close properly cleans up resources."""
        # Arrange
        mock_executor = mocker.Mock()
        mock_executor.shutdown = AsyncMock()

        mock_perplexity = mocker.Mock()
        mock_perplexity.aclose = AsyncMock()

        mock_exa = mocker.Mock()
        mock_exa.aclose = AsyncMock()

        mock_openrouter = mocker.Mock()
        mock_openrouter.aclose = AsyncMock()

        service = InfoServiceGroup()
        service._executor = mock_executor
        service._perplexity = mock_perplexity
        service._exa = mock_exa
        service._openrouter = mock_openrouter

        # Act
        await service.close()

        # Assert
        mock_executor.shutdown.assert_called_once()
        mock_perplexity.aclose.assert_called_once()
        mock_exa.aclose.assert_called_once()
        mock_openrouter.aclose.assert_called_once()


class TestInfoServiceIntegration:
    """Integration tests for the InfoServiceGroup class."""

    @pytest.mark.asyncio
    async def test_info_service_perplexity_search_integration(self, mocker):
        """Test end-to-end Perplexity search request handling."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={"perplexity": "result"})

        # Mock the match_endpoint function
        mocker.patch(
            "khive.services.info.info_service.match_endpoint",
            return_value=mock_endpoint,
        )

        # Mock the PerplexityChatRequest class and capture the created instance
        perplexity_request_mock = mocker.patch(
            "khive.connections.providers.perplexity_.PerplexityChatRequest"
        )

        service = InfoServiceGroup()

        # Create a mock for InfoRequest that bypasses validation
        with (
            patch("khive.services.info.parts.InfoRequest") as MockRequest,
            patch("khive.services.info.parts.InfoSearchParams") as MockSearchParams,
        ):
            mock_request = MockRequest.return_value
            mock_request.action = InfoAction.SEARCH

            mock_params = MockSearchParams.return_value
            mock_params.provider = SearchProvider.PERPLEXITY
            mock_params.provider_params = {"query": "test"}

            mock_request.params = mock_params

            # Act
            response = await service.handle_request(mock_request)

        # Assert
        assert response.success is True
        assert response.action_performed == InfoAction.SEARCH
        assert response.content == {"perplexity": "result"}

        # Verify that the endpoint was called (without checking the exact mock object)
        assert mock_endpoint.call.call_count == 1
        # Verify that the PerplexityChatRequest constructor was called
        assert perplexity_request_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_info_service_exa_search_integration(self, mocker):
        """Test end-to-end Exa search request handling."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={"exa": "result"})

        # Mock the match_endpoint function
        mocker.patch(
            "khive.services.info.info_service.match_endpoint",
            return_value=mock_endpoint,
        )

        # Mock the ExaSearchRequest class and capture the created instance
        exa_request_mock = mocker.patch(
            "khive.connections.providers.exa_.ExaSearchRequest"
        )

        service = InfoServiceGroup()

        # Create a mock for InfoRequest that bypasses validation
        with (
            patch("khive.services.info.parts.InfoRequest") as MockRequest,
            patch("khive.services.info.parts.InfoSearchParams") as MockSearchParams,
        ):
            mock_request = MockRequest.return_value
            mock_request.action = InfoAction.SEARCH

            mock_params = MockSearchParams.return_value
            mock_params.provider = SearchProvider.EXA
            mock_params.provider_params = {"query": "test"}

            mock_request.params = mock_params

            # Act
            response = await service.handle_request(mock_request)

        # Assert
        assert response.success is True
        assert response.action_performed == InfoAction.SEARCH
        assert response.content == {"exa": "result"}

        # Verify that the endpoint was called (without checking the exact mock object)
        assert mock_endpoint.call.call_count == 1
        # Verify that the ExaSearchRequest constructor was called
        assert exa_request_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_info_service_consult_integration(self, mocker):
        """Test end-to-end consult request handling."""
        # Arrange
        mock_endpoint = mocker.Mock()
        mock_endpoint.call = AsyncMock(return_value={"openrouter": "result"})

        # Mock the match_endpoint function
        mocker.patch(
            "khive.services.info.info_service.match_endpoint",
            return_value=mock_endpoint,
        )

        # Mock the executor map method
        mock_map = AsyncMock(return_value=[("model1", {"openrouter": "result"})])
        mock_executor = mocker.Mock()
        mock_executor.map = mock_map

        service = InfoServiceGroup()
        service._executor = mock_executor

        # Create a mock for InfoRequest that bypasses validation
        with (
            patch("khive.services.info.parts.InfoRequest") as MockRequest,
            patch("khive.services.info.parts.InfoConsultParams") as MockConsultParams,
        ):
            mock_request = MockRequest.return_value
            mock_request.action = InfoAction.CONSULT

            mock_params = MockConsultParams.return_value
            mock_params.question = "test question"
            mock_params.models = ["model1"]
            mock_params.system_prompt = "test prompt"

            mock_request.params = mock_params

            # Act
            response = await service.handle_request(mock_request)

        # Assert
        assert response.success is True
        assert response.action_performed == InfoAction.CONSULT
        assert "model1" in response.content
