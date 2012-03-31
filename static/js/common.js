$(document).ready(function(){
    function getPositionSuccess( position ){
        var lat = position.coords.latitude;
        var lng = position.coords.longitude;
        alert( "您所在的位置： 经度" + lat + "，纬度" + lng );
        if(typeof position.address !== "undefined"){
                var country = position.address.country;
                var province = position.address.region;
                var city = position.address.city;
                alert('您位于' + country + province + '省' + city + '市');
        }
    };

    function getPositionError(error){
        switch(error.code){
            case error.TIMEOUT:
                alert("连接超时，请重试");
                break;
            case error.PERMISSION_DENIED:
                alert("您拒绝了使用位置共享服务，查询已取消");
                break;
            case error.POSITION_UNAVAILABLE: 
                alert("亲爱的火星用户，非常抱歉，我们暂时无法为您所在的星球提供位置服务");
                break;
        }
    };

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(getPositionSuccess, getPositionError);
    }else{
        alert('浏览器不支持 geolocation ');
    }

})
