# coding: utf-8
from typing import List

import numpy as np
import pandas as pd
import xarray as xr

from nuwe_cmadaas.music import apiinterface_pb2 as pb


class RequestInfo(object):
    def __init__(
            self,
            error_code: int = 0,
            error_message: str = "",
            request_elements: str = "",
            request_params: str = "",
            request_time: str = "",
            response_time: str = "",
            row_count: int = 0,
            take_time: int = 0,
            col_count: int = 0,
            pb_request_info: pb.RequestInfo = None,
    ):
        self.error_code = error_code
        self.error_message = error_message
        self.request_elements = request_elements
        self.request_params = request_params
        self.request_time = request_time
        self.response_time = response_time
        self.row_count = row_count
        self.take_time = take_time
        self.col_count = col_count

        if pb_request_info is not None:
            self.load_protobuf(pb_request_info)

    def load_protobuf(self, request_info: pb.RequestInfo):
        self.error_code = request_info.errorCode
        self.error_message = request_info.errorMessage
        self.request_elements = request_info.requestElems
        self.request_params = request_info.requestParams
        self.request_time = request_info.requestTime
        self.response_time = request_info.responseTime
        self.row_count = request_info.rowCount
        self.take_time = request_info.takeTime
        self.col_count = request_info.colCount

    @classmethod
    def create_from_protobuf(cls, request_info: pb.RequestInfo):
        r = RequestInfo()
        r.load_protobuf(request_info)
        return r


class ResponseData(object):
    def __init__(
            self,
            request: RequestInfo = None
    ):
        self.request = request

    def load_from_protobuf_content(self, content: bytes):
        pass

    @classmethod
    def create_from_protobuf(cls, content: bytes):
        data = cls()
        data.load_from_protobuf_content(content)
        return data

    def to_pandas(self):
        raise NotImplementedError()

    def to_xarray(self):
        raise NotImplementedError()


class Array2D(ResponseData):
    protobuf_object_type = pb.RetArray2D

    def __init__(
            self,
            data: np.ndarray = None,
            request: RequestInfo = None,
            element_names: List[str] = None,
            row_count: int = 0,
            col_count: int = 0,
    ):
        super().__init__(request=request)
        self.data = data
        self.element_names = element_names
        self.row_count = row_count
        self.col_count = col_count

    def to_pandas(self) -> pd.DataFrame:
        df = pd.DataFrame(self.data, columns=self.element_names)
        return df

    def load_from_protobuf_content(self, content: bytes):
        protobuf_object = self.protobuf_object_type()
        protobuf_object.ParseFromString(content)
        self.load_from_protobuf_object(protobuf_object)

    def load_from_protobuf_object(self, ret_array_2d: pb.RetArray2D):
        self.request = RequestInfo.create_from_protobuf(ret_array_2d.request)
        self.element_names = ret_array_2d.elementNames
        if self.request.error_code != 0:
            return

        self.row_count = ret_array_2d.request.rowCount
        # self.col_count = ret_array_2d.request.colCount
        total_count = len(ret_array_2d.data)
        self.col_count = int(total_count/self.row_count)
        assert(self.col_count == ret_array_2d.request.colCount)

        self.data = np.array(ret_array_2d.data).reshape([self.row_count, self.col_count])


class DataBlock(ResponseData):
    protobuf_object_type = pb.RetDataBlock

    def __init__(
            self,
            data_name: str = None,
            data: bytes = None,
            request: RequestInfo = None,
    ):
        super().__init__(request=request)
        self.data_name = data_name
        self.data = data

    def load_from_protobuf_content(self, content: bytes):
        protobuf_object = self.protobuf_object_type()
        protobuf_object.ParseFromString(content)
        self.load_from_protobuf_object(protobuf_object)

    def load_from_protobuf_object(self, ret_data_block: pb.RetDataBlock):
        self.request = RequestInfo.create_from_protobuf(ret_data_block.request)
        self.data_name = ret_data_block.dataName
        self.data = ret_data_block.byteArray


class GridArray2D(ResponseData):
    protobuf_object_type = pb.RetGridArray2D

    def __init__(
            self,
            data: List[float] = None,
            request: RequestInfo = None,
            start_lat: float = 0,
            start_lon: float = 0,
            end_lat: float = 0,
            end_lon: float = 0,
            lat_count: int = 0,
            lon_count: int = 0,
            lon_step: float = 0,
            lat_step: float = 0,
            lats: List[float] = None,
            lons: List[float] = None,
            units: str = "",
            user_element_name: str = "",
    ):
        super().__init__(request=request)
        self.data = data
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.end_lat = end_lat
        self.end_lon = end_lon
        self.lat_count = lat_count
        self.lon_count = lon_count
        self.lon_step = lon_step
        self.lat_step = lat_step
        self.lats = lats
        self.lons = lons
        self.units = units
        self.user_element_name = user_element_name

    def to_xarray(self) -> xr.DataArray:
        coords = {}
        if len(self.lats) > 0:
            lats = self.lats
        else:
            lats = np.linspace(
                self.start_lat, self.end_lat, self.lat_count,
                endpoint=True
            )

        if len(self.lons) > 0:
            lons = self.lats
        else:
            lons = np.linspace(
                self.start_lon, self.end_lon, self.lon_count,
                endpoint=True
            )

        coords["latitude"] = xr.Variable(
            "latitude",
            lats,
            attrs={
                "units": "degrees_north",
                "standard_name": "latitude",
                "long_name": "latitude"
            },
        )
        coords["longitude"] = xr.Variable(
            "longitude",
            lons,
            attrs={
                "units": "degrees_east",
                "standard_name": "longitude",
                "long_name": "longitude"
            }
        )

        dims = ("latitude", "longitude")

        field = xr.DataArray(
            self.data,
            dims=dims,
            coords=coords,
            attrs={
                "units": self.units,
            },
            name=self.user_element_name,
        )

        return field

    def load_from_protobuf_content(self, content: bytes):
        protobuf_object = self.protobuf_object_type()
        protobuf_object.ParseFromString(content)
        self.load_from_protobuf_object(protobuf_object)

    def load_from_protobuf_object(self, ret_grid_array_2d: pb.RetGridArray2D):
        self.request = RequestInfo.create_from_protobuf(ret_grid_array_2d.request)

        if self.request.error_code != 0:
            return

        self.start_lat = ret_grid_array_2d.startLat
        self.start_lon = ret_grid_array_2d.startLon
        self.end_lat = ret_grid_array_2d.endLat
        self.end_lon = ret_grid_array_2d.endLon
        self.lat_count = ret_grid_array_2d.latCount
        self.lon_count = ret_grid_array_2d.lonCount
        self.lon_step = ret_grid_array_2d.lonStep
        self.lat_step = ret_grid_array_2d.latStep

        if ret_grid_array_2d.lats is not None:
            self.lats = ret_grid_array_2d.lats
        else:
            self.lats = [self.start_lat + i * self.lat_step for i in range(self.lat_count)]

        if ret_grid_array_2d.lons is not None:
            self.lons = ret_grid_array_2d.lons
        else:
            self.lons = [self.start_lon + i * self.lon_step for i in range(self.lon_count)]

        self.units = ret_grid_array_2d.units
        self.user_element_name = ret_grid_array_2d.userEleName

        row_count = self.request.row_count
        data_count = len(ret_grid_array_2d.data)
        col_count = int(data_count/row_count)
        self.data = np.array(ret_grid_array_2d.data).reshape([row_count, col_count])


class FileInfo(object):
    def __init__(
            self,
            file_name: str = "",
            save_path: str = "",
            suffix: str = "",
            size: str = "",
            file_url: str = "",
            image_base64: str = "",
            attributes: List[str] = None,
    ):
        self.file_name = file_name
        self.save_path = save_path
        self.suffix = suffix
        self.size = size
        self.file_url = file_url
        self.image_base64 = image_base64
        self.attributes = attributes

    @classmethod
    def create_from_protobuf(cls, pb_file_info: pb.FileInfo):
        return FileInfo(
            file_name=pb_file_info.fileName,
            save_path=pb_file_info.savePath,
            suffix=pb_file_info.suffix,
            size=pb_file_info.size,
            file_url=pb_file_info.fileUrl,
            image_base64=pb_file_info.imgBase64,
            attributes=pb_file_info.attributes,
        )


class FilesInfo(ResponseData):
    protobuf_object_type = pb.RetFilesInfo

    def __init__(self, files_info: List[FileInfo] = None, request: RequestInfo = None):
        super().__init__(request)
        self.files_info = files_info

    def load_from_protobuf_content(self, content: bytes):
        protobuf_object = self.protobuf_object_type()
        protobuf_object.ParseFromString(content)
        self.load_from_protobuf_object(protobuf_object)

    def load_from_protobuf_object(self, ret_files_info: pb.RetFilesInfo):
        self.request = RequestInfo.create_from_protobuf(ret_files_info.request)

        if self.request.error_code != 0:
            return

        files_info = ret_files_info.fileInfos
        self.files_info = [FileInfo.create_from_protobuf(info) for info in files_info]


class GridVector2D(ResponseData):
    protobuf_object_type = pb.RetGridVector2D

    def __init__(
            self,
            u_data: List[float] = None,
            v_data: List[float] = None,
            request: RequestInfo = None,
            start_lat: float = 0,
            start_lon: float = 0,
            end_lat: float = 0,
            end_lon: float = 0,
            lat_count: int = 0,
            lon_count: int = 0,
            lon_step: float = 0,
            lat_step: float = 0,
            lats: List[float] = None,
            lons: List[float] = None,
            u_element_name: str = "",
            v_element_name: str = "",
    ):
        super().__init__(request)
        self.u_data = u_data
        self.v_data = v_data
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.end_lat = end_lat
        self.end_lon = end_lon
        self.lat_count = lat_count
        self.lon_count = lon_count
        self.lon_step = lon_step
        self.lat_step = lat_step
        self.lats = lats
        self.lons = lons
        self.u_element_name = u_element_name
        self.v_element_name = v_element_name

    def load_from_protobuf_content(self, content: bytes):
        protobuf_object = self.protobuf_object_type()
        protobuf_object.ParseFromString(content)
        self.load_from_protobuf_object(protobuf_object)

    def load_from_protobuf_object(self, ret_grid_vector_2d: pb.RetGridVector2D):
        self.request = RequestInfo.create_from_protobuf(ret_grid_vector_2d.request)

        if self.request.error_code != 0:
            return

        self.start_lat = ret_grid_vector_2d.startLat
        self.start_lon = ret_grid_vector_2d.startLon
        self.end_lat = ret_grid_vector_2d.endLat
        self.end_lon = ret_grid_vector_2d.endLon
        self.lat_count = ret_grid_vector_2d.latCount
        self.lon_count = ret_grid_vector_2d.lonCount
        self.lon_step = ret_grid_vector_2d.lonStep
        self.lat_step = ret_grid_vector_2d.latStep

        self.lats = ret_grid_vector_2d.lats
        self.lons = ret_grid_vector_2d.lons

        self.u_element_name = ret_grid_vector_2d.u_EleName
        self.v_element_name = ret_grid_vector_2d.v_EleName

        row_count = self.lat_count
        col_count = self.lon_count
        self.u_data = np.array(ret_grid_vector_2d.u_datas).reshape([row_count, col_count])
        self.v_data = np.array(ret_grid_vector_2d.v_data2).reshape([row_count, col_count])


class GridScalar2D(ResponseData):
    protobuf_object_type = pb.RetGridScalar2D

    def __init__(
            self,
            data: List[float] = None,
            request: RequestInfo = None,
            start_lat: float = 0,
            start_lon: float = 0,
            end_lat: float = 0,
            end_lon: float = 0,
            lat_count: int = 0,
            lon_count: int = 0,
            lon_step: float = 0,
            lat_step: float = 0,
            lats: List[float] = None,
            lons: List[float] = None,
            units: str = "",
            user_element_name: str = "",
    ):
        super().__init__(request)
        self.data = data
        self.start_lat = start_lat
        self.start_lon = start_lon
        self.end_lat = end_lat
        self.end_lon = end_lon
        self.lat_count = lat_count
        self.lon_count = lon_count
        self.lon_step = lon_step
        self.lat_step = lat_step
        self.lats = lats
        self.lons = lons
        self.units = units
        self.user_element_name = user_element_name

    def load_from_protobuf_content(self, content: bytes):
        protobuf_object = self.protobuf_object_type()
        protobuf_object.ParseFromString(content)
        self.load_from_protobuf_object(protobuf_object)

    def load_from_protobuf_object(self, ret_grid_scalar_2d: pb.RetGridScalar2D):
        self.request = RequestInfo.create_from_protobuf(ret_grid_scalar_2d.request)

        if self.request.error_code != 0:
            return

        self.start_lat = ret_grid_scalar_2d.startLat
        self.start_lon = ret_grid_scalar_2d.startLon
        self.end_lat = ret_grid_scalar_2d.endLat
        self.end_lon = ret_grid_scalar_2d.endLon
        self.lat_count = ret_grid_scalar_2d.latCount
        self.lon_count = ret_grid_scalar_2d.lonCount
        self.lon_step = ret_grid_scalar_2d.lonStep
        self.lat_step = ret_grid_scalar_2d.latStep

        self.lats = ret_grid_scalar_2d.lats
        self.lons = ret_grid_scalar_2d.lons

        self.user_element_name = ret_grid_scalar_2d.userEleName

        row_count = self.lat_count
        col_count = self.lon_count
        self.data = np.array(ret_grid_scalar_2d.data).reshape([row_count, col_count])
