package handlers

import (
	"github.com/gin-gonic/gin"
)

func Home(context *gin.Context) {
	context.HTML(200, "index.html", gin.H{
		"title": "Home Page",
	})
}
