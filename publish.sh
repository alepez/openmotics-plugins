#!/bin/sh
if [ $# -le 3 ]
then
  echo "Usage: ./`basename $0` <package> <ip/hostname of gateway> <username>"
else
  checksum=`md5sum $1 | cut -d ' ' -f 1`
  if [ -z "${4}" ]; then read -s -p "Enter password: " password; else password="${4}"; fi
  echo
  login=`curl -sk -X GET "https://$2/login?username=$3&password=$password"`
  success=`echo $login | grep -Po '"success": \K\w+'`
  if [ "$success" = "true" ]
  then
    token=`echo $login | grep -Po '"token": "\K\w+'`
    result=`curl -sk --form "package_data=@$1" --form md5=$checksum --form token=$token -X POST "https://$2/install_plugin"`
    success=`echo $result | grep -Po '"success": \K\w+'`
    if [ "$success" = "true" ]
    then
      echo "Publish succeeded"
    else
      error=`echo $result | grep -Po '"msg": "\K[^"]+'`
      echo "Publish failed: $error"
    fi
  else
    echo "Login failed"
  fi
fi
