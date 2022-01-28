<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    version="1.0">

    <xsl:output method="xml" indent="yes"/>

    <xsl:template name="string-replace-all">
      <xsl:param name="text" />
      <xsl:param name="replace" />
      <xsl:param name="by" />
      <xsl:choose>
        <xsl:when test="contains($text, $replace)">
          <xsl:value-of select="substring-before($text,$replace)" />
          <xsl:value-of select="$by" />
          <xsl:call-template name="string-replace-all">
            <xsl:with-param name="text" select="substring-after($text,$replace)" />
            <xsl:with-param name="replace" select="$replace" />
            <xsl:with-param name="by" select="$by" />
          </xsl:call-template>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="$text" />
        </xsl:otherwise>
      </xsl:choose>
    </xsl:template>

    <xsl:template match="node()|@*">
        <xsl:copy>
            <xsl:apply-templates select="node()|@*"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="/rss/channel/item/enclosure">
        <xsl:copy>
            <xsl:attribute name="url">
                <xsl:text>https://dts.podtrac.com/redirect.m4a/</xsl:text>
                <xsl:value-of select="substring-after(@url, 'https://')"/>
                <!-- There used to be a bug in the way podtrac redirects the anchor.fm
                     URL.  It does the URL encoding translation incorrectly and
                     so the URL it redirects to doesn't work.  We need to change
                     the https%3A%2F%2F in the anchor URL to https:// which is
                     only a problem with podtrac/anchor.  It seems like podtrac
                     has fixed this issue but I'll leave this code here in case
                     it breaks again >
                <xsl:call-template name="string-replace-all">
                    <xsl:with-param name="text" select="substring-after(@url, 'https://')"/>
                    <xsl:with-param name="replace" select="'%3A%2F%2F'"/>
                    <xsl:with-param name="by" select="'://'"/>
                </xsl:call-template -->
            </xsl:attribute>
            <xsl:apply-templates select="@*[not(local-name()='url')]|node()"/>
        </xsl:copy>
    </xsl:template>
</xsl:stylesheet>
