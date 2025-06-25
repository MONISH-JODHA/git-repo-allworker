package handlers

import (
	"github.com/gin-gonic/gin"
)

func Bootcamp(context *gin.Context) {
	context.HTML(200, "bootcamp.html", gin.H{
		"title": "Bootcamp Page",
	})
}
